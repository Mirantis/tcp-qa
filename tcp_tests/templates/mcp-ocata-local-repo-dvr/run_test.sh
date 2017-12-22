export REPOSITORY_SUITE=2017.12
export SALT_MODELS_SYSTEM_REPOSITORY=https://gerrit.mcp.mirantis.local.test/salt-models/reclass-system
export SALT_FORMULAS_REPO=https://gerrit.mcp.mirantis.local.test/salt-formulas

# Offline deployment simulation, requests to the apt01 node are redirected to publicly available repositories
export FORMULA_REPOSITORY="deb [arch=amd64] http://apt.mirantis.local.test/xenial ${REPOSITORY_SUITE} salt"
export FORMULA_GPG="http://apt.mirantis.local.test/public.gpg"
export SALT_REPOSITORY="deb http://apt.mirantis.com/xenial/salt/2016.3/ ${REPOSITORY_SUITE} main"
export SALT_GPG="http://apt.mirantis.local.test/public.gpg"
export UBUNTU_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/${REPOSITORY_SUITE}/ubuntu xenial main universe restricted"
export UBUNTU_UPDATES_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/${REPOSITORY_SUITE}/ubuntu xenial-updates main universe restricted"
export UBUNTU_SECURITY_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/${REPOSITORY_SUITE}/ubuntu xenial-security main universe restricted"

# Offline deployment simulation, requests to the apt01 node are redirected to an 'offline apt node' with mirrors of repositories
export FORMULA_REPOSITORY="deb [arch=amd64] http://apt.mirantis.local.test/ubuntu-xenial ${REPOSITORY_SUITE} salt extra"
export FORMULA_GPG="http://apt.mirantis.local.test/public.gpg"
export SALT_REPOSITORY="deb [arch=amd64] http://apt.mirantis.local.test/ubuntu-xenial/ ${REPOSITORY_SUITE} salt/2016.3 main"
export SALT_GPG="http://apt.mirantis.local.test/public.gpg"
export UBUNTU_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/ubuntu xenial main universe restricted"
export UBUNTU_UPDATES_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/ubuntu xenial-updates main universe restricted"
export UBUNTU_SECURITY_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/ubuntu xenial-security main universe restricted"
