"""Online, nonce-bound parent authorization. Never trusts a radio's ready flag.

P-256 signatures are fixed-width r||s. Wire layout is shared with parent_auth.h.
The caller binds MQTT requests to the certificate-scoped topic; root requests
are accepted only on the selected root's USB control channel.
"""
import base64
import hashlib
import json
from pathlib import Path
import struct
import threading
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.exceptions import InvalidSignature
from changan_ugv.nodes.inventory import authorized, root_of, valid_id

REQUEST = struct.Struct('!4sB32s32s16s6s16s6s')
REQUEST_SIZE = REQUEST.size + 64  # 177
GRANT_SIZE = REQUEST_SIZE + 65 + 1 + 1 + 4 + 64  # 312
TTL = 20
LEVELS = {'ugv_root': 1, 'ugv': 2, 'uav': 3, 'micro_uav': 4}


def field(value):
    return valid_id(value).encode('ascii').ljust(32, b'\0')


def identity(raw):
    value = raw.rstrip(b'\0').decode('ascii')
    if field(value) != raw:
        raise ValueError('noncanonical_identity')
    return value


def public_bytes(key):
    return key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def private_key(raw):
    if len(raw) != 32:
        raise ValueError('invalid_parent_private_key')
    return ec.derive_private_key(int.from_bytes(raw, 'big'), ec.SECP256R1())


def sign(key, data):
    r, s = utils.decode_dss_signature(key.sign(data, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')


def verify(public, signature, data):
    if len(signature) != 64:
        raise ValueError('invalid_signature_size')
    try:
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public)
        key.verify(utils.encode_dss_signature(int.from_bytes(signature[:32], 'big'),
                   int.from_bytes(signature[32:], 'big')), data, ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError) as exc:
        raise ValueError('parent_signature_invalid') from exc


def decode_request(data):
    if len(data) != REQUEST_SIZE:
        raise ValueError('invalid_parent_request_size')
    magic, purpose, node, root, boot, ap, nonce, child = REQUEST.unpack(data[:REQUEST.size])
    if magic != b'PAR1' or purpose not in (0, 1) or not any(boot) or not any(nonce):
        raise ValueError('invalid_parent_request')
    if not any(ap) or ap[0] & 1 or not any(child) or child[0] & 1:
        raise ValueError('invalid_parent_radio')
    return dict(node=identity(node), root=identity(root), purpose=purpose, boot=boot,
                ap=ap, nonce=nonce, child=child)


class ParentAuthority:
    def __init__(self, directory, inventory_loader, root_id, certificate=None, clock=time.monotonic):
        self.directory = Path(directory)
        self.inventory_loader, self.root_id = inventory_loader, valid_id(root_id)
        self.certificate, self.clock = certificate, clock
        self.lock = threading.RLock()
        self.window, self.count = 0., 0

    def issue(self, request, authenticated_node, *, usb=False):
        values = decode_request(request)
        if values['node'] != authenticated_node or values['root'] != self.root_id:
            raise ValueError('parent_transport_identity_mismatch')
        with self.lock:
            now = self.clock()
            if now - self.window >= 1:
                self.window, self.count = now, 0
            self.count += 1
            if self.count > 32:
                raise ValueError('parent_authority_busy')
            entries = {e['node_id']: e for e in self.inventory_loader()['nodes']}
            entry = entries.get(authenticated_node)
            if not entry or root_of(entry) != self.root_id or not authorized(entry):
                raise ValueError('parent_not_authorized')
            level = LEVELS[entry['role']]
            if level == 4 or (usb != (level == 1)) or (usb and authenticated_node != self.root_id):
                raise ValueError('parent_role_or_transport_invalid')
            bindings = json.loads((self.directory / 'bindings.json').read_text(encoding='utf-8'))
            authority_public=(self.directory / 'authority.pub').read_bytes()
            if bindings.get('schema')!=1 or bindings.get('authority_sha256')!=hashlib.sha256(authority_public).hexdigest():
                raise ValueError('parent_authority_binding_mismatch')
            binding = bindings['nodes'][authenticated_node]
            if binding['root_id'] != self.root_id or binding['role'] != entry['role']:
                raise ValueError('parent_enrollment_mismatch')
            if not usb:
                if not self.certificate or self.certificate(authenticated_node) != binding['certificate_sha256']:
                    raise ValueError('parent_certificate_binding_mismatch')
            public = bytes.fromhex(binding['public_key'])
            verify(public, request[-64:], request[:-64])
            key = private_key((self.directory / 'authority.key').read_bytes())
            if public_bytes(key.public_key()) != authority_public:
                raise ValueError('parent_authority_key_mismatch')
            revision=entry.get('admission_revision',0)
            if type(revision) is not int or not 0<=revision<=0xffffffff:
                raise ValueError('invalid_parent_admission_revision')
            body = request + public + bytes([level, TTL]) + struct.pack('!I', revision)
            return body + sign(key, body)

    def mqtt_reply(self, node, body):
        if set(body) != {'v', 'type', 'proof'} or body['v'] != 1 or body['type'] != 'parent.auth.request':
            raise ValueError('invalid_parent_auth_message')
        proof = base64.b64decode(body['proof'], validate=True)
        grant = self.issue(proof, node)
        return json.dumps(dict(v=1, type='parent.auth.grant', proof=base64.b64encode(grant).decode()),
                          separators=(',', ':'))


def validate_grant(grant, authority_public, request_values, expected_level):
    """Reference verifier for interop/adversarial host tests (no network or UTC)."""
    if len(grant) != GRANT_SIZE:
        raise ValueError('invalid_parent_grant_size')
    verify(authority_public, grant[-64:], grant[:-64])
    values = decode_request(grant[:REQUEST_SIZE])
    if any(values[key] != value for key, value in request_values.items()):
        raise ValueError('parent_challenge_mismatch')
    public = grant[REQUEST_SIZE:REQUEST_SIZE+65]
    verify(public, grant[REQUEST.size:REQUEST_SIZE], grant[:REQUEST.size])
    if grant[REQUEST_SIZE+65] != expected_level or grant[REQUEST_SIZE+66] != TTL:
        raise ValueError('parent_level_or_lease_invalid')
    return values
