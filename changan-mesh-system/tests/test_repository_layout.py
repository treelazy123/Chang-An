"""Repository migration checks: no IDF configure, firmware compile or COM access."""
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from _bootstrap import bootstrap
bootstrap()
from changan_ugv.protocol.frames import encode,Decoder
from sync_runtime import sync_runtime,stopped_service

class ProtocolContracts(unittest.TestCase):
    def test_fixed_vectors_roundtrip_in_fragments(self):
        for vector in json.loads((ROOT/'protocols/v1/frames.json').read_text(encoding='utf-8'))['vectors']:
            wire=bytes.fromhex(vector['hex'])
            self.assertEqual(wire,encode(vector['message']))
            decoder=Decoder();decoded=[]
            for offset in range(0,len(wire),3):decoded.extend(decoder.feed(wire[offset:offset+3]))
            self.assertEqual([vector['message']],decoded)
    def test_independent_car_implementation_matches_contract(self):
        car=Path(os.environ.get('CHANGAN_CAR_TERMINAL',str(ROOT.parent/'changan-car-terminal')))
        path=car/'car_terminal/protocol.py'
        if not path.is_file():self.skipTest('Independent car repository is not present')
        spec=importlib.util.spec_from_file_location('car_protocol_contract',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for vector in json.loads((ROOT/'protocols/v1/frames.json').read_text(encoding='utf-8'))['vectors']:
            wire=bytes.fromhex(vector['hex'])
            self.assertEqual(wire,module.encode(vector['message']))
            self.assertEqual([vector['message']],module.Decoder().feed(wire))

class MigrationBoundaries(unittest.TestCase):
    def test_third_party_source_bytes_preserved(self):
        manifest=json.loads((ROOT/'docs/migration-source-manifest.json').read_text(encoding='utf-8'))
        vendors={p.name for p in (ROOT/'third_party').iterdir() if p.is_dir()}
        checked=0
        for entry in manifest['files']:
            path=Path(entry['path'])
            if len(path.parts)>2 and path.parts[0]=='components' and path.parts[1] in vendors:
                new=ROOT/'third_party'/Path(*path.parts[1:])
                self.assertEqual(entry['sha256'],hashlib.sha256(new.read_bytes()).hexdigest(),str(new))
                checked+=1
        self.assertGreater(checked,100)
    def test_all_roles_resolve_real_sources_without_building(self):
        cmake=shutil.which('cmake')
        if not cmake:
            candidates=sorted(Path('C:/Espressif/tools/cmake').glob('*/bin/cmake.exe'))
            if candidates:cmake=str(candidates[-1])
        if not cmake:self.skipTest('CMake unavailable for script-only wiring check')
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp)
            for name in ('ca.pem','client.pem','client.key'):
                p=temp/'secrets/test-node'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
            # idf_component_register stub checks declarations only; no compiler/IDF is invoked.
            preamble=r"""cmake_minimum_required(VERSION 3.22)
function(idf_component_register)
    cmake_parse_arguments(COMP "" "" "SRCS;INCLUDE_DIRS;REQUIRES;EMBED_TXTFILES" ${ARGN})
    foreach(source IN LISTS COMP_SRCS COMP_EMBED_TXTFILES)
        get_filename_component(resolved "${source}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_LIST_DIR}")
        if(NOT EXISTS "${resolved}")
            message(FATAL_ERROR "Missing declared source: ${resolved}")
        endif()
        file(APPEND "${CHECK_OUTPUT}" "${resolved}\n")
    endforeach()
endfunction()
"""
            for role,app in (('pc_root','root'),('ugv','ugv'),('uav','uav'),('micro_uav','micro_uav')):
                for mqtt in (0,1):
                    output=temp/f'{role}-{mqtt}.txt'
                    script=temp/'check.cmake'
                    s=preamble+f'\nset(CHECK_OUTPUT "{output.as_posix()}")\nset(MESH_SYSTEM_ROOT "{temp.as_posix()}")\nset(CONFIG_APP_NODE_ID "test-node")\nset(CONFIG_APP_ROLE_{role.upper()} 1)\nset(CONFIG_APP_TRANSPORT_MQTT_SERIAL {mqtt})\n'
                    for directory in ('main','components/mqtt_serial','components/car_gateway','components/task_agent'):
                        s+=f'include("{(ROOT/"firmware"/directory/"CMakeLists.txt").as_posix()}")\n'
                    script.write_text(s,encoding='utf-8')
                    result=subprocess.run([cmake,'-P',str(script)],capture_output=True,text=True)
                    self.assertEqual(0,result.returncode,result.stderr)
                    sources=output.read_text()
                    self.assertIn(f'/apps/{app}/app.c',sources)
                    for other in {'root','ugv','uav','micro_uav'}-{app}:
                        self.assertNotIn(f'/apps/{other}/app.c',sources)
                    self.assertEqual(role=='ugv' and bool(mqtt),'/apps/ugv/serial_tunnel.c' in sources)
                    self.assertEqual(role=='pc_root','/apps/root/car_gateway.c' in sources)
                    self.assertIn('/task_agent/task_agent.c',sources)

class RuntimeHandoff(unittest.TestCase):
    def setUp(self):
        from provision_mqtt import provision
        import contextlib,io
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name)/'source';self.target=Path(self.temp.name)/'target'
        with contextlib.redirect_stdout(io.StringIO()):provision(self.source)
        shutil.copytree(self.source,self.target)
        from changan_ugv.tasks.store import Store
        self.store=Store(self.source/'runtime/tasks.sqlite3')
        self.addCleanup(self.store.close)
        # Raw extra table proves a live-WAL snapshot, independent of the business schema.
        self.store.db.execute('CREATE TABLE migration_probe(value)')
        self.store.db.execute('INSERT INTO migration_probe VALUES (42)');self.store.db.commit()
    def test_copy_includes_wal_and_rewrites_config_preserving_keys(self):
        import sqlite3
        before=(self.target/'secrets/ca.key').read_bytes()
        # Keep the source connection open: WAL data must be included by backup().
        backup=sync_runtime(self.source,self.target)
        with closing(sqlite3.connect(self.target/'runtime/tasks.sqlite3')) as db:
            self.assertEqual(42,db.execute('SELECT value FROM migration_probe').fetchone()[0])
        self.assertTrue(backup.is_dir())
        self.assertEqual(before,(self.target/'secrets/ca.key').read_bytes())
        config=(self.target/'runtime/mosquitto.conf').read_text()
        self.assertNotIn(self.source.as_posix(),config)
        self.assertIn(self.target.as_posix(),config)
    def test_active_controller_blocks_state_sync(self):
        with stopped_service(self.source):
            with self.assertRaisesRegex(ValueError,'running'):sync_runtime(self.source,self.target)
        self.assertFalse((self.target/'runtime/tasks.sqlite3').exists())
    def test_different_ca_is_rejected_without_overwriting(self):
        old=(self.target/'secrets/ca.pem').read_bytes()
        (self.source/'secrets/ca.pem').write_text('wrong CA')
        with self.assertRaisesRegex(ValueError,'CA differs'):sync_runtime(self.source,self.target)
        self.assertEqual(old,(self.target/'secrets/ca.pem').read_bytes())
if __name__=='__main__':unittest.main()
