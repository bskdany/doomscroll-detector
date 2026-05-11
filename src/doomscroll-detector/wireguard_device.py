import os
from pathlib import Path

def get_wireguard_configs():
    # Get home directory
    home_dir = str(Path.home())
    config_dict = {}
    
    conf_files = Path(home_dir).glob('*.conf')
    
    for conf_file in conf_files:
        try:
            with open(conf_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip().startswith('Address = '):
                        address = line.strip().split('=')[1].strip().split('/')[0]
                        config_dict[address] = conf_file.name
                        break
        except Exception as e:
            print(f"Error reading {conf_file}: {e}")
    
    return config_dict

def get_hostname_by_ip(ip):
    configs = get_wireguard_configs()
    return configs.get(ip, None)

if __name__ == "__main__":
    configs = get_wireguard_configs()
    print("Wireguard Configurations:")
    for filename, address in configs.items():
        print(f"{filename}: {address}")