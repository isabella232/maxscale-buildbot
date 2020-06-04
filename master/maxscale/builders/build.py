import os

from buildbot.config import BuilderConfig
from buildbot.plugins import util, steps
from maxscale import workers
from maxscale.builders.support import common, support

ENVIRONMENT = {
    "JOB_NAME": util.Property("buildername"),
    "BUILD_ID": util.Interpolate('%(prop:buildnumber)s'),
    "BUILD_NUMBER": util.Interpolate('%(prop:buildnumber)s'),
    "MDBCI_VM_PATH": util.Property('MDBCI_VM_PATH'),
    "box": util.Property('box'),
    "target": util.Property('target'),
    "cmake_flags": util.Property('cmake_flags'),
    "do_not_destroy_vm": util.Property('do_not_destroy_vm'),
    "build_experimental": util.Property('build_experimental'),
    "try_already_running": util.Property('try_already_running'),
    "run_upgrade_test": util.Property('run_upgrade_test'),
    "old_target": util.Property('old_target'),
    "ci_url": util.Property('ci_url')
}


@util.renderer
def configureBuildProperties(properties):
    return {
        "mdbciConfig": util.Interpolate("%(prop:MDBCI_VM_PATH)s/%(prop:box)s-%(prop:buildername)s-%(prop:buildnumber)s")
    }


def remoteBuildMaxscale():
    """This script will be run on the worker"""
    if not os.path.exists("BUILD/mdbci"):
        os.mkdir("default-maxscale-branch")
        os.chdir("default-maxscale-branch")
        subprocess.run(["git", "clone", repository])
        os.chdir("..")
    if not os.path.isdir("BUILD"):
        shutil.copytree("default-maxscale-branch/MaxScale/BUILD", ".")
    if not os.path.isdir("BUILD/mdbci"):
        shutil.copytree("default-maxscale-branch/MaxScale/BUILD/mdbci", "BUILD/")
    results = subprocess.run(["BUILD/mdbci/build.sh"])
    sys.exit(results.returncode)


def createBuildSteps():
    buildSteps = []
    buildSteps.extend(common.configureMdbciVmPathProperty())
    buildSteps.append(steps.SetProperties(properties=configureBuildProperties))
    buildSteps.extend(common.cloneRepository())
    buildSteps.extend(support.executePythonScript(
        "Build MaxScale using MDBCI", remoteBuildMaxscale))
    buildSteps.extend(common.cleanBuildDir())
    buildSteps.extend(common.destroyVirtualMachine())
    buildSteps.extend(common.removeLock())
    buildSteps.extend(common.syncRepod())
    buildSteps.append(steps.ShellCommand(
        name="Rsync builds results to repo server",
        command=[util.Interpolate('rsync -avz --progress -e ssh ~/repository/%(prop:target)s/%(prop:box)s vagrant@max-tst-01.mariadb.com:/home/vagrant/repository/%(prop:target)s/')],
        timeout=1800,
    ))
    return buildSteps


def createBuildFactory():
    factory = util.BuildFactory()
    buildSteps = createBuildSteps()
    factory.addSteps(buildSteps)
    return factory


BUILDERS = [
    BuilderConfig(
        name="build",
        workernames=workers.workerNames(),
        factory=createBuildFactory(),
        nextWorker=common.assignWorker,
        nextBuild=common.assignBuildRequest,
        tags=["build"],
        env=ENVIRONMENT,
        collapseRequests=False,
        defaultProperties={
            "try_already_running": None
        }
    )
]
