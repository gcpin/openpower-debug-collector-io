# dumptool

A Python command-line tool for managing OpenBMC dumps on systems using the
phal-next backend.

## Overview

`dumptool` simplifies dump management on OpenBMC systems by providing an
intuitive command-line interface for common dump operations.

### Why dumptool?

On OpenBMC systems, dumps are critical for debugging hardware and firmware
issues. However, managing these dumps traditionally requires:

- Complex D-Bus commands with lengthy object paths
- Knowledge of specific D-Bus interfaces and methods
- Manual parsing of D-Bus output

`dumptool` addresses these challenges by:

- **Simplifying Operations**: Single commands replace complex D-Bus calls
- **Improving Usability**: Clear, formatted output instead of raw D-Bus data
- **Reducing Errors**: Type validation and helpful error messages
- **Saving Time**: Quick access to dump information without memorizing D-Bus
  paths

### What it does

- **List dumps**: View all dumps or filter by type with formatted output
- **Create dumps**: Generate BMC, hostboot, hardware, or SBE dumps on demand
- **Query dumps**: Get detailed information about specific dumps
- **Delete dumps**: Clean up old or unnecessary dumps
- **Smart categorization**: Automatically identifies hostboot and SBE dumps

## Usage

```bash
dumptool <command> [options]
```

## Commands

### help

Display help information.

```bash
dumptool --help
dumptool -h
```

### list

List all dumps or filter by type.

```bash
dumptool list [--type TYPE]
```

- `--type`: Optional filter. Accepted values: `bmc`, `system`, `hostboot`,
  `hardware`, `sbe`

### create

Create a new dump.

```bash
dumptool create --type TYPE [--error-id ERROR_ID] [--failing-id FAILING_UNIT_ID]
```

- `--type`: **Required**. Dump type to create. Accepted values: `bmc`,
  `hostboot`, `hardware`, `sbe`
- `--error-id`: Error Log ID (required for `hardware`; optional for `hostboot`
  and `sbe`). Accepts decimal or hex (e.g. `0xDEADBEEF`).
- `--failing-id`: Failing Unit ID (required for `sbe`; optional for `hardware`).
  Integer.

### delete

Delete a dump by ID.

```bash
dumptool delete DUMP_ID
```

- `DUMP_ID`: ID of the dump to delete

### get-info

Get detailed information about a specific dump.

```bash
dumptool get-info DUMP_ID
```

- `DUMP_ID`: ID of the dump

## Examples

### Getting Help

Display general help:

```bash
$ dumptool --help
usage: dumptool [-h] <command> ...

OpenBMC Dump Management Tool

Supported dump types:
  bmc
  hostboot
  hardware
  sbe

Commands:
  list                List available dumps
  create              Create a dump
  delete              Delete a dump
  get-info            Show dump information

Examples:
  dumptool list
  dumptool list --type bmc
  dumptool list --type hostboot
  dumptool list --type hardware
  dumptool list --type sbe

  dumptool create --type bmc
  dumptool create --type hostboot
  dumptool create --type hardware --error-id <ERROR_ID>
  dumptool create --type sbe --failing-id <FAILING_UNIT_ID>

  dumptool get-info <DUMP_ID>
  dumptool delete <DUMP_ID>

Placeholders:
  <ERROR_ID>         Error Log ID (e.g. 0xDEADBEEF)
  <FAILING_UNIT_ID>  Failing Unit ID (e.g. 1)
  <DUMP_ID>          Dump ID
```

Get help for the create command:

```bash
$ dumptool create --help
usage: dumptool create [-h] --type {bmc,hostboot,hardware,sbe}
                       [--error-id ERROR_ID] [--failing-id FAILING_ID]

Create a new dump.

options:
  -h, --help            show this help message and exit
  --type {bmc,hostboot,hardware,sbe}
                        Type of dump to create.
  --error-id ERROR_ID   Error Log ID (required for hardware, optional for hostboot and sbe).
  --failing-id FAILING_ID
                        Failing Unit ID (required for sbe, optional for hardware).
```

### Listing Dumps

List all dumps:

```bash
$ dumptool list
ID         Type         Size(KB)     Start Time           End Time             Status
1          bmc          256 KB       2024-04-27 10:30:00  2024-04-27 10:30:05  Completed
20000001   hostboot     512 KB       2024-04-27 11:00:00  2024-04-27 11:00:10  Completed
30000001   sbe          128 KB       2024-04-27 12:00:00  2024-04-27 12:00:03  Completed
```

List only BMC dumps:

```bash
$ dumptool list --type bmc
ID         Type         Size(KB)     Start Time           End Time             Status
1          bmc          256 KB       2024-04-27 10:30:00  2024-04-27 10:30:05  Completed
```

List only system dumps (includes hostboot, hardware, and SBE subtypes):

```bash
$ dumptool list --type system
ID         Type         Size(KB)     Start Time           End Time             Status
20000001   hostboot     512 KB       2024-04-27 11:00:00  2024-04-27 11:00:10  Completed
30000001   sbe          128 KB       2024-04-27 12:00:00  2024-04-27 12:00:03  Completed
```

### Creating Dumps

Create a BMC dump:

```bash
$ dumptool create --type bmc
✔ Dump created successfully
Dump ID : 1
```

Create a hostboot dump:

```bash
$ dumptool create --type hostboot
✔ Dump created successfully
Dump ID : 20000001
```

```bash
$ dumptool create --type hardware --error-id 0xDEADBEEF
✔ Dump created successfully
Dump ID : 20000002
```

```bash
$ dumptool create --type sbe --failing-id 1
✔ Dump created successfully
Dump ID : 30000001
```

Omitting required arguments prints an error:

```bash
$ dumptool create --type hardware
✖ Hardware dump requires --error-id

$ dumptool create --type sbe
✖ SBE dump requires --failing-id
```

### Getting Dump Information

Get details for a specific dump:

```bash
$ dumptool get-info 1
ID           : 1
Type         : bmc
Size (KB)    : 256 KB
Start Time   : 2024-04-27 10:30:00
End Time     : 2024-04-27 10:30:05
Status       : Completed
Offloaded    : False
```

Get details for a hostboot dump:

```bash
$ dumptool get-info 20000001
ID           : 20000001
Type         : hostboot
Size (KB)    : 512 KB
Start Time   : 2024-04-27 11:00:00
End Time     : 2024-04-27 11:00:10
Status       : Completed
Offloaded    : False
```

### Deleting Dumps

Delete a dump by ID:

```bash
$ dumptool delete 1
Dump deleted successfully
```

Delete multiple dumps:

```bash
$ dumptool delete 1
Dump deleted successfully
$ dumptool delete 2
Dump deleted successfully
```

## Common Workflows

Check for recent dumps:

```bash
dumptool list
```

Create and verify a BMC dump:

```bash
dumptool create --type bmc
dumptool list --type bmc
dumptool get-info <DUMP_ID>
```

Create and verify a hardware dump:

```bash
dumptool create --type hardware --error-id 0xDEADBEEF
dumptool list --type system
dumptool get-info <DUMP_ID>
```

Clean up old dumps:

```bash
dumptool list
dumptool delete 1
dumptool delete 2
```

## Requirements

- Python 3.6 or later
- busctl (systemd)
- OpenBMC system with IBM dump extensions
- D-Bus system bus access
