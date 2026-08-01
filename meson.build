project(
    'openpower-debug-collector',
    'cpp',
    meson_version: '>=1.1.1',
    default_options: ['warning_level=3', 'werror=true', 'cpp_std=c++23'],
    license: 'Apache-2.0',
    version: '1.1.0',
)

cxx = meson.get_compiler('cpp')

sdbusplus_dep = dependency('sdbusplus')

if cxx.has_header('CLI/CLI.hpp')
    CLI11_dep = declare_dependency()
else
    CLI11_dep = dependency('CLI11')
endif

phosphorlogging = dependency(
    'phosphor-logging',
    fallback: ['phosphor-logging', 'phosphor_logging_dep'],
)

realpath_prog = find_program('realpath')

phal_backend = get_option('phal_backend')

conf_data = configuration_data()
extra_deps = []
watchdog_lib = []

# Build PHAL abstraction library FIRST (shared by dump and watchdog)
# Only build if a backend is selected
if phal_backend != 'none'
    subdir('phal')
endif

if get_option('hostboot-dump-collection').allowed()
    conf_data.set('WATCHDOG_DUMP_COLLECTION', true)
    if phal_backend != 'none'
        extra_deps += [phal_abstraction_dep]        # Use PHAL abstraction
    endif
    subdir('watchdog')
else
    conf_data.set('WATCHDOG_DUMP_COLLECTION', false)
endif

configure_file(output: 'config.h', configuration: conf_data)

if get_option('dump-collection').allowed()
    subdir('dump')
endif

# Install dumptool Python package for phal-next backend
if phal_backend == 'next'
    python = import('python').find_installation('python3')

    # Install the dumptool package
    python.install_sources(
        'tools/dumptool/__init__.py',
        'tools/dumptool/__main__.py',
        'tools/dumptool/cli.py',
        'tools/dumptool/models.py',
        subdir: 'dumptool',
    )

    python.install_sources(
        'tools/dumptool/clients/dbus_client.py',
        'tools/dumptool/clients/__init__.py',
        subdir: 'dumptool/clients',
    )

    python.install_sources(
        'tools/dumptool/services/dump_service.py',
        'tools/dumptool/services/__init__.py',
        subdir: 'dumptool/services',
    )

    # Create wrapper script in /usr/bin
    configure_file(
        input: 'tools/dumptool-wrapper.sh',
        output: 'dumptool',
        configuration: configuration_data(),
        install: true,
        install_dir: get_option('bindir'),
        install_mode: 'rwxr-xr-x',
    )

    dumptool_test_env = environment()
    dumptool_test_env.set(
        'PYTHONPATH',
        meson.current_source_dir() / 'tools',
    )
    dumptool_test_env.set('PYTHONDONTWRITEBYTECODE', '1')
    test(
        'dumptool-unit-tests',
        python,
        args: [
            '-m',
            'unittest',
            'discover',
            '-s',
            meson.current_source_dir() / 'tools/dumptool/tests',
            '-v',
        ],
        env: dumptool_test_env,
        suite: 'dumptool',
    )
endif

deps = [CLI11_dep, sdbusplus_dep, phosphorlogging, extra_deps]

if get_option('hostboot-dump-collection').allowed() and get_option(
    'phal_backend',
) == 'legacy'
    executable(
        'watchdog_timeout',
        'watchdog_timeout.cpp',
        dependencies: deps,
        link_with: watchdog_lib,
        implicit_include_directories: true,
        install: true,
    )
endif

executable(
    'checkstop_app',
    'checkstop_app.cpp',
    dependencies: deps,
    implicit_include_directories: true,
    install: true,
)
