import itertools
from . import build
from . import run_test
from . import download_shell_scripts
from . import destroy
from . import remove_lock
from . import smart_remove_lock
from . import cleanup
from . import build_and_test
from . import build_and_simple_test
from . import remove_lock_snapshot
from . import run_test_snapshot
from . import smart_remove_lock_snapshot

MAXSCALE_BUILDERS = list(itertools.chain(
    build.BUILDERS,
    run_test.BUILDERS,
    download_shell_scripts.BUILDERS,
    destroy.BUILDERS,
    remove_lock.BUILDERS,
    smart_remove_lock.BUILDERS,
    cleanup.BUILDERS,
    build_and_test.BUILDERS,
    build_and_simple_test.BUILDERS,
    remove_lock_snapshot.BUILDERS,
    run_test_snapshot.BUILDERS,
    smart_remove_lock_snapshot.BUILDERS
))
