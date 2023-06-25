# Ansible playbooks to setup my computers

## Install

```
sudo apt update && sudo apt install curl git
git clone git@github.com:Jibux/personal_ansible
cd personal_ansible
./install_ansible.sh
```

## Desktop setup

```
ansible-playbook playbooks/desktop.yml -l jibux-taf -D 
```

### Just packages

```
ansible-playbook playbooks/packages.yml -l jibux-taf -D 
```

### Just config and scripts

```
ansible-playbook playbooks/setup_files.yml -l jibux-taf -D 
```

## Jibux services

See [README.md](roles/jibux_svc/README.md).

```bash
ansible-playbook playbooks/jibux_svc.yml -l jibux-taf -D
```

## MEGA cli

See [README.md](roles/mega/README.md).

```bash
ansible-playbook playbooks/mega.yml -l jibux-taf -D
```

## Home server

```bash
ansible-playbook playbooks/home_server_all.yml -D
```

