"""An OS lock prevents duplicate controller-001 sessions; released automatically on process exit."""
import os
from pathlib import Path
class Lease:
    def __init__(self,secret=None, *, lock_file=None):
        self.file=None
        path=Path(lock_file) if lock_file is not None else Path(secret)/'.controller.lock'
        path.parent.mkdir(parents=True,exist_ok=True)
        stream=path.open('a+b')
        try:
            stream.seek(0,2)
            if not stream.tell():stream.write(b'0');stream.flush()
            stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise ValueError('Another UGV manager owns controller-001. Use UGV Service through the running service, or stop the standalone manager first.') from exc
        self.file=stream
    def close(self):
        if self.file is not None:self.file.close();self.file=None
