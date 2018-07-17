import subprocess
import sys
import os

subDir = "prodCfg"

def openFromFileName(filename):
    fullName = subDir + "/" + filename
    semaphore = open("semaphore.txt", "r+", encoding = "utf-8")
    cont = ""
    while "write" not in cont:
        semaphore.seek(0)
        cont = semaphore.readline()

    semaphore.seek(0)
    semaphore.write("reads")
    semaphore.close()
    cfg = open("cfg.txt", "w+", encoding = "utf-8")
    with open(fullName, "r+", encoding = "utf-8") as input:
        for line in input.readlines():
            cfg.write(line)
        input.close()
    cfg.close()
    subprocess.Popen(["py", "main.py"])

if __name__ == "__main__":
    filenames = os.listdir(subDir)
    for filename in filenames:
        if "cfg" in filename:
            openFromFileName(filename)
