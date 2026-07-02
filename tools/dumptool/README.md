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
- **Create dumps**: Generate BMC, system, resource, or faultlog dumps on demand
- **Query dumps**: Get detailed information about specific dumps
- **Delete dumps**: Clean up old or unnecessary dumps
- **Smart categorization**: Automatically identifies hostboot and SBE dumps
  based on ID ranges

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

- `--type`: Optional filter (bmc, system, resource, faultlog)

### create

Create a new dump.

```bash
dumptool create [--type TYPE]
```

- `--type`: Dump type to create (default: bmc)
  - Accepted values: bmc, system, resource, faultlog

### delete

Delete a dump by ID.

```bash
dumptool delete DUMP_ID
```

- `DUMP_ID`: Numeric ID of the dump to delete

### get-info

Get detailed information about a specific dump.

```bash
dumptool get-info DUMP_ID
```

- `DUMP_ID`: Numeric ID of the dump

## Examples

### Getting Help

Display general help:

```bash
$ dumptool --help
usage: dumptool [-h] {list,create,delete,get-info} ...

Dump Management Tool

positional arguments:
  {list,create,delete,get-info}
    list                List all dumps
    create              Create a dump
    delete              Delete a dump
    get-info            Get dump details

optional arguments:
  -h, --help            show this help message and exit
```

Get help for the create command:

```bash
$ dumptool create --help
usage: dumptool create [-h] [--type TYPE]

optional arguments:
  -h, --help   show this help message and exit
  --type TYPE  Dump type (accepted values: bmc, system, resource, faultlog)
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

List only system dumps:

```bash
$ dumptool list --type system
ID         Type         Size(KB)     Start Time           End Time             Status
20000001   hostboot     512 KB       2024-04-27 11:00:00  2024-04-27 11:00:10  Completed
30000001   sbe          128 KB       2024-04-27 12:00:00  2024-04-27 12:00:03  Completed
```

### Creating Dumps

Create a BMC dump (default):

```bash
$ dumptool create
✔ Dump created successfully
```

Create a system dump:

```bash
$ dumptool create --type system
✔ Dump created successfully
```

Create a resource dump:

```bash
$ dumptool create --type resource
✔ Dump created successfully
```

Create a faultlog dump:

```bash
$ dumptool create --type faultlog
✔ Dump created successfully
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

Clean up old dumps:

```bash
dumptool list
dumptool delete 1
dumptool delete 2
```

## Requirements

- Python 3.6 or later
- busctl (systemd)
- OpenBMC system with phal-next backend
- D-Bus system bus access
