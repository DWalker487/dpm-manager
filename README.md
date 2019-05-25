# dpm-mananger
File management scripts for DPM storage using GFAL. python2,3 compatible. 
Enhancements/bugfixes are always welcome.

For help, run ./gfal_manager -h

The default setup can be modified by changing "config.py". The possible options are:

  * `default_user` sets the user name. This can be overwritten with `--user`. By
    default this is set to be the same as the system user name `$USER`.

  * `file_count_reprint_no` print the number files at the beginning and the end
    if more then `file_count_reprint_no` file or folders are found.

  * `DPM` Sets the remote file server.

  * `dir_colour` Display colours of directories.

  * `exe_colour` Display colours of executables.

  * `use_fnmatch` If `true` shell wild-cards will be used for searches with the
    `-w` flag. Setting it to `false` will use regular expressions instead.

  * `protocol_default` Set the default protocol for use with gfal.

  * `protocol_list` Set the protocol for file listing with gfal. Read only protocols 
    are usually fastest.

  * `protocol_delete` Set the protocol for file deletion with gfal. Read/write protocols 
    required.

  * `protocol_download` Set the protocol for file download with gfal. Read/write protocols 
    required.

  * `protocol_upload` Set the protocol for file upload with gfal. Read/write protocols 
    required.

  * `protocol_move` Set the protocol for file moving with gfal. Read/write protocols 
    required.
