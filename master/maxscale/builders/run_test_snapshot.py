import os

from buildbot.plugins import steps, util
from buildbot.config import BuilderConfig
from buildbot.process.buildstep import ShellMixin
from buildbot.steps import shell
from twisted.internet import defer
from . import builders_config
from . import common
from maxscale.config import constants

DEFAULT_PROPERTIES = {
    "name": "test01",
    "branch": "master",
    "repository": constants.MAXSCALE_REPOSITORY,
    "target": "develop",
    "box": constants.BOXES[0],
    "product": 'mariadb',
    "version": constants.DB_VERSIONS[0],
    "test_set": "-LE HEAVY",
    "ci_url": constants.CI_SERVER_URL,
    "smoke": "yes",
    "big": "yes",
    "backend_ssl": 'no',
    "logs_dir": os.environ['HOME'] + "/LOGS",
    "template": 'default',
    "snapshot_name": 'clean',
    "test_branch": 'master',
}

class RunTestSnapshotSetPropertiesStep(ShellMixin, steps.BuildStep):
    name = 'Set properties'

    def __init__(self, **kwargs):
        kwargs = self.setupShellMixin(kwargs, prohibitArgs=['command'])
        steps.BuildStep.__init__(self, **kwargs)

    @defer.inlineCallbacks
    def run(self):
        # BUILD_TIMESTAMP property
        cmd = yield self.makeRemoteShellCommand(
            command=['date', "+%Y-%m-%d %H-%M-%S"],
            collectStdout=True)
        yield self.runCommand(cmd)
        self.setProperty('BUILD_TIMESTAMP', cmd.stdout[0:-1], 'setProperties')
        # SHELL_SCRIPTS_PATH property
        cmd = yield self.makeRemoteShellCommand(
            command='echo "`pwd`/{}"'.format(builders_config.WORKER_SHELL_SCRIPTS_RELATIVE_PATH),
            collectStdout=True)
        yield self.runCommand(cmd)
        self.setProperty('SHELL_SCRIPTS_PATH', cmd.stdout[0:-1], 'setProperties')
        # WORKSPACE property
        cmd = yield self.makeRemoteShellCommand(
            command='pwd',
            collectStdout=True)
        yield self.runCommand(cmd)
        self.setProperty('WORKSPACE', cmd.stdout[0:-1], 'setProperties')
        # JOB_NAME property
        self.setProperty('JOB_NAME', 'run_test_snapshot', 'setProperties')
        # custom_builder_id property
        self.setProperty('custom_builder_id', '102', 'setProperties')
        # BUILD_ID property
        self.setProperty(
            'BUILD_ID',
            "{}{}".format(self.getProperty('custom_builder_id'),
                          self.getProperty('buildnumber')),
            'setProperties'
        )
        defer.returnValue(0)


def create_factory():
    factory = util.BuildFactory()

    factory.addStep(common.SetDefaultPropertiesStep(default_properties=DEFAULT_PROPERTIES, haltOnFailure=True))

    factory.addStep(RunTestSnapshotSetPropertiesStep(haltOnFailure=True))

    factory.addStep(steps.Trigger(
        name="Call the 'download_shell_scripts' scheduler",
        schedulerNames=['download_shell_scripts'],
        waitForFinish=True,
        haltOnFailure=True,
        copy_properties=['SHELL_SCRIPTS_PATH']
    ))
    factory.addStep(shell.SetProperty(
        name="Set the 'env' property",
        command="bash -c env",
        haltOnFailure=True,
        extract_fn=common.save_env_to_property,
        env={
            "WORKSPACE": util.Property('WORKSPACE'),
            "JOB_NAME": util.Property('JOB_NAME'),
            "BUILD_ID": util.Property('BUILD_ID'),
            "BUILD_NUMBER": util.Property('BUILD_ID'),
            "BUILD_TIMESTAMP": util.Property('BUILD_TIMESTAMP'),
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
            "logs_dir": util.Property('logs_dir'),
            "template": util.Property('template'),
            "test_branch": util.Property('branch'),
            "try_already_running": util.Property('try_already_running')
        }))

    factory.addStep(steps.Git(
        repourl=util.Property('repository'),
        mode='incremental',
        branch=util.Property('branch'),
        haltOnFailure=True))

    # Run test snapshot and collect
    factory.addStep(steps.ShellCommand(
        name="Run the 'run_test_snapshot_and_collect.sh' script",
        command=['sh', util.Interpolate('%(prop:SHELL_SCRIPTS_PATH)s/run_test_snapshot_and_collect.sh')],
        haltOnFailure=True,
        env=util.Property('env')))

    # Parse build log
    factory.addStep(steps.ShellCommand(
        name="Run the 'parse_build_log.sh' script",
        command=['sh', util.Interpolate('%(prop:SHELL_SCRIPTS_PATH)s/parse_build_log.sh')],
        haltOnFailure=True,
        env=util.Property('env')))

    # Write build results
    factory.addStep(steps.ShellCommand(
        name="Run the 'write_build_results.sh' script",
        command=['sh', util.Interpolate('%(prop:SHELL_SCRIPTS_PATH)s/write_build_results.sh')],
        haltOnFailure=True,
        env=util.Property('env')))

    # Create env coredumps
    factory.addStep(steps.ShellCommand(
        name="Run the 'create_env_coredumps.sh' script",
        command=['sh', util.Interpolate('%(prop:SHELL_SCRIPTS_PATH)s/create_env_coredumps.sh')],
        haltOnFailure=True,
        env=util.Property('env')))

    # Save the '$WORKSPACE/results_$BUILD_ID' content to the 'build_results_content' property
    factory.addStep(shell.SetProperty(
        name="Save the '$WORKSPACE/results_$BUILD_ID' content to the 'build_results_content' property",
        property="build_results_content",
        command=util.Interpolate("cat %(prop:WORKSPACE)s/results_%(prop:BUILD_ID)s"),
        haltOnFailure=True, ))

    # Save the '$WORKSPACE/coredumps_$BUILD_ID' content to the 'coredumps_results_content' property
    factory.addStep(shell.SetProperty(
        name="Save the '$WORKSPACE/coredumps_$BUILD_ID' content to the 'coredumps_results_content' property",
        property="coredumps_results_content",
        command=util.Interpolate("cat %(prop:WORKSPACE)s/coredumps_%(prop:BUILD_ID)s"),
        haltOnFailure=True, ))

    factory.addStep(steps.Trigger(
        name="Call the 'smart_remove_lock_snapshot' scheduler",
        schedulerNames=['smart_remove_lock_snapshot'],
        waitForFinish=True,
        alwaysRun=True,
        copy_properties=[
            "try_already_running",
            "box",
        ],
        set_properties={
            "name": util.Interpolate('%(prop:box)s-%(prop:product)s-%(prop:version)s-permanent'),
            "build_full_name": util.Interpolate('%(prop:JOB_NAME)s-%(prop:BUILD_ID)s')
        }
    ))

    # Workspace cleanup
    factory.addStep(steps.ShellCommand(
        name="Workspace cleanup",
        command=common.clean_workspace_command,
        alwaysRun=True,
        env=util.Property('env')))

    return factory


BUILDERS = [
    BuilderConfig(
        name="run_test_snapshot",
        workernames=["worker1"],
        factory=create_factory(),
        tags=['test'],
        env=dict(os.environ))
]