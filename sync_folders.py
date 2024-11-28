# TODO update mod folder if local timestamp is newer than remote timestamp

import os
import json
from paramiko.sftp_client import SFTPClient
from fabric import Connection
from fabric.transfer import Transfer

MODS_FILE = 'mods.txt'
CONFIG_FILE = 'config.json'

if not os.path.exists(CONFIG_FILE):
    raise Exception(f'Could not find {CONFIG_FILE}')

if not os.path.exists(MODS_FILE):
    raise Exception(f'Could not find mod list file {MODS_FILE}')

mods = []
with open(MODS_FILE, 'r', encoding='utf-8') as f:
    for line in f.read().splitlines():
        try:
            int(line)
            mods.append(line)
        except:
            continue

print(f'Syncing {len(mods)} mods from {MODS_FILE}')

with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)

props_to_check = [
    'local_mod_folder',
    'remote_mod_folder',
    'remote_ip',
    'remote_port',
    'remote_user',
    'remote_pwd'
]

for prop in props_to_check:
    if not prop in config:
        raise Exception(f'Could not find property {prop} in config.json')
    
local_mod_folder = config['local_mod_folder']
if not os.path.exists(local_mod_folder):
    raise Exception(f'Local mod folder {local_mod_folder} does not exist')

ip = config['remote_ip']
user = config['remote_user']
pwd = config['remote_pwd']

try:
    port = int(config['remote_port'])
except:
    rp = config['remote_port']
    raise Exception(f'Could not parse port number {rp}')

print(f'Connecting to {user}@{ip}:{port}')
con = Connection(ip, user, port, connect_kwargs = {
    "password": pwd,
    "look_for_keys": False
})
tran = Transfer(con)

remote_mod_folder = config['remote_mod_folder']
if not tran.is_remote_dir(remote_mod_folder):
    raise Exception(f'Could not find remote mod folder {remote_mod_folder}')
print('Connection Success!')

ignore_mod = '111111111'

remote_mods = []
sftp: SFTPClient = tran.sftp
for file in sftp.listdir(remote_mod_folder):
    if file == ignore_mod:
        continue
    remote_file = remote_mod_folder + '/' + file
    if not tran.is_remote_dir(remote_file):
        continue
    try:
        int(file)
        remote_mods.append(file)
    except:
        continue

print(f'Found {len(remote_mods)} mods in remote mod folder')

print('\nChecking remote mods against mods list')
removed = 0
for mod in remote_mods:
    remote_folder = remote_mod_folder + '/' + mod
    if not mod in mods:
        print(f'Removing {mod} from remote')
        sftp.rmdir(remote_folder)
        sftp.remove(remote_folder + '.mod')
        removed += 1

def transfer_folder(folder: str):
    local_folder = local_mod_folder + '/' + folder
    remote_folder = remote_mod_folder + '/' + folder
    for file in os.listdir(local_folder):
        local_file = local_folder + '/' + file
        remote_file = remote_folder + '/' + file
        if os.path.isfile(local_file):
            print(f'Transferring {remote_file}')
            tran.put(local_file, remote_file)
        
        if os.path.isdir(local_file):
            sftp.mkdir(remote_folder)
            transfer_folder(folder + '/' + file)

print('\nAdding local mods to remote')
added = 0
skipped = 0
for mod in mods:
    local_folder = local_mod_folder + '/' + mod
    if not os.path.exists(local_folder):
        skipped += 1
        print(f'Could not find local folder for {mod}')
        continue
    
    remote_folder = remote_mod_folder + '/' + mod
    if tran.is_remote_dir(remote_folder):
        print(f'Found remote mod: {mod}')
        continue
    print(f'Transferring {mod} to remote')
    transfer_folder(mod)
    tran.put(local_folder + '.mod', remote_folder + '.mod')
    added += 1

if added > 0:
    print(f'Added {added} mods')

if skipped > 0:
    print(f'Skipped {skipped} mods that were not found')

if removed > 0:
    print(f'Removed {removed} mods')

print('DONE! :)')