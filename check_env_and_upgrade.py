#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: hawcat
@time: 2024/1/17 11:36 
@file: check_env_and_upgrade.py
@project: O3_fabric
@describe: TODO
"""
import subprocess
import os
import configparser
import argparse
import zipfile

import requests
from tqdm import tqdm


def get_pip(python_base):
    url = "https://bootstrap.pypa.io/get-pip.py"

    response = requests.get(url)
    if response.status_code == 200:
        with open(os.path.join(python_base, "get-pip.py"), 'wb') as file:
            file.write(response.content)
        print("get-pip.py downloaded successfully.")
    else:
        print("Failed to download get-pip.py. Status code:", response.status_code)


def download_python_embeddable(version) -> str:
    base_url = f"https://www.python.org/ftp/python/{version}/"

    # Construct the embeddable package URL
    embeddable_url = f"{base_url}python-{version}-embed-amd64.zip"

    # Create a directory to save the downloaded file
    temp_dir = "embeddable_packages"
    os.makedirs(temp_dir, exist_ok=True)

    # Download the embeddable package
    response = requests.get(embeddable_url, stream=True)
    file_size = int(response.headers['Content-Length'])
    chunk_size = 1024
    num_bars = int(file_size / chunk_size)
    file_path = os.path.join(temp_dir, f"python-{version}-embed-amd64.zip")

    with open(file_path, 'wb') as fp:  # cover mode
        for chunk in tqdm(iterable=response.iter_content(chunk_size=chunk_size), total=num_bars,
                          desc=f'Downloading [python-{version}-embed-amd64.zip]', unit='KB'):
            fp.write(chunk)

    # shutil.rmtree(temp_dir)
    print("Downloaded Python embeddable package for version {}".format(version))
    return file_path


def config_loader(project_name) -> str:
    config = configparser.ConfigParser()
    config.read("config.ini")
    try:
        python_path = config.get(project_name, 'py_env')
        if not python_path:
            raise ValueError("No python env in config.ini, check project name if in the config.ini")
    except Exception:
        raise ValueError("No python env in config.ini, check project name if in the config.ini")

    return python_path


def install_package(python_path, package_name, pip_args=None):
    try:
        # 使用subprocess调用系统命令安装包
        if pip_args:
            command = (f"{python_path} -m pip install {package_name} --no-warn-script-location "
                       f"{pip_args}")
            subprocess.check_call(command, shell=True)
        else:
            command = [python_path, "-m", "pip", "install", package_name,
                       "--no-warn-script-location"]
            subprocess.check_call(command, shell=True)
        print(f"Package '{package_name}' installed successfully.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install package '{package_name}'. Error: {e}")


def upgrade_config():
    pass


def read_requirements(project_dir) -> list:
    requirements = []
    with open(os.path.join(project_dir, "requirements.txt"), "r") as f:
        for line in f:
            requirements.append(line.strip())

    return requirements


def create_env(python_directory, install_version):
    os.makedirs(python_directory, exist_ok=True)
    site_packages = os.path.join(python_directory, "Lib", "site-packages")

    zip_path = download_python_embeddable(install_version)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(python_directory)
    print(f"Create python env in {python_directory} done!")

    version_out = os.popen(f"{python_directory}/python.exe -V")
    version_list = version_out.readline().replace(".", " ").split(" ")
    python_version = "".join(version_list[:3]).lower()

    get_pip(python_directory)

    try:
        subprocess.run(f"{python_directory}/python.exe {python_directory}/get-pip.py", shell=True)
        print("pip install done!")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install pip. Error: {e}")

    with open(os.path.join(python_directory, f"{python_version}._pth"), "a") as f:
        f.write(f"import site")
    print(f"Add {python_version}._pth done!")

    with open(os.path.join(site_packages, "project_path.pth"), "w") as f:
        f.write("import sys;import os;sys.path.insert(0,os.path.dirname(sys.argv[0]));")
    print("Add project_path.pth done!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--project", type=str, help="project name/ python path")
    parser.add_argument("-d", "--dir", type=str, help="project dir")
    parser.add_argument("-new", "--new_env", type=str, help="env path")
    parser.add_argument("-v", "--version", type=str, help="python version")
    parser.add_argument("-torch", "--torch", action="store_true", help="whether install pytorch")

    args = parser.parse_args()
    # print(args.new_env)

    create_env(args.new_env, args.version) if args.new_env else print("No need to create new env.")
    python = os.path.join(args.new_env, "python.exe") if args.new_env else args.project

    requirement_list = read_requirements(args.dir)

    if args.torch:
        torch_suit = ["torch", "torchvision", "torchaudio"]
        for package in torch_suit:
            install_package(python, package, "--index-url https://download.pytorch.org/whl/cu118")

    for requirement in requirement_list:
        install_package(python, requirement)
