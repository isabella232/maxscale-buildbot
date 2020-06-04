from buildbot.plugins import steps, util
from buildbot.config import BuilderConfig
from maxscale.builders.support import common, support
from maxscale import workers
from maxscale.builders import run_test

RUN_TEST_SNAPSHOT_ENVIRONMENT = {
    "WORKSPACE": util.Interpolate('%(prop:builddir)s/build'),
    "JOB_NAME": util.Property("buildername"),
    "BUILD_ID": util.Interpolate('%(prop:buildername)s-%(prop:buildnumber)s'),
    "BUILD_NUMBER": util.Interpolate('%(prop:buildnumber)s'),
    "BUILD_TIMESTAMP": util.Interpolate('%(kw:datetime)s',
                                        datetime=common.getFormattedDateTime("%Y-%m-%d %H-%M-%S")),
    "BUILD_LOG_PARSING_RESULT": 'Build log parsing finished with an error',
    "name": util.Property('name'),
    "snapshot_name": util.Property('snapshot_name'),
    "target": util.Property('target'),
    "box": util.Property('box'),
    "product": util.Property('product'),
    "version": util.Property('version'),
    "test_set": util.Property('test_set'),
    "ci_url": util.Property('ci_url'),
    "smoke": util.Property('smoke'),
    "big": util.Property('big'),
    "backend_ssl": util.Property('backend_ssl'),
    "template": util.Property('template'),
    "test_branch": util.Property('branch'),
    "use_valgrind": util.Property("use_valgrind"),
}


def createRunTestSnapshotSteps():
    testSnapshotSteps = []
    # run_test_snapshot.sh script does not take 'name' argument, but instead defines its own
    # which consists of environmental variables ${box}-${product}-${version}-permanent.
    # This step overwrites property 'name' which is set from scheduler to match 'name' in script
    testSnapshotSteps.append(steps.SetProperty(
        property="name",
        value=util.Interpolate("%(prop:box)s-%(prop:product)s-%(prop:version)s-permanent")))
    testSnapshotSteps.extend(common.configureMdbciVmPathProperty())
    testSnapshotSteps.extend(common.cloneRepository())
    testSnapshotSteps.append(steps.SetProperties(properties=run_test.configureCommonProperties))
    testSnapshotSteps.extend(common.remoteRunScriptAndLog("run_test_snapshot.sh",
                                                          name="Run MaxScale tests using snapshots"))
    testSnapshotSteps.extend(common.parseCtestLog())
    testSnapshotSteps.extend(common.findCoredump())
    testSnapshotSteps.extend(common.writeBuildsResults())
    testSnapshotSteps.extend(common.showTestResult(alwaysRun=True))
    testSnapshotSteps.extend(common.removeSnapshotLock())
    testSnapshotSteps.extend(common.removeLock())
    testSnapshotSteps.extend(common.cleanBuildDir())
    return testSnapshotSteps


def createTestShapshotFactory():
    factory = util.BuildFactory()
    testSnapshotSteps = createRunTestSnapshotSteps()
    factory.addSteps(testSnapshotSteps)
    return factory


BUILDERS = [
    BuilderConfig(
        name="run_test_snapshot",
        workernames=workers.workerNames(),
        nextWorker=common.assignWorker,
        factory=createTestShapshotFactory(),
        tags=['test'],
        env=RUN_TEST_SNAPSHOT_ENVIRONMENT,
        properties={
            "scriptName": "run_test_snapshot.sh"
        },
        defaultProperties={
            "try_already_running": None
        }
    ),
]
