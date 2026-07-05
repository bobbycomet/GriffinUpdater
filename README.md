# Discord Updater

### Version 2.0 is being worked on, and it will be renamed, as it will handle more than Discord, such as the OpenTabletdriver. This is not affiliated with any of the projects themselves.

### UPDATE: I fixed the .sh file. There was a bug with the way it handled the .timer. It is now fixed. Uninstall with sudo apt remove, then sudo apt install to fix it, if you have the old one. Afterwards, it will just need sudo apt update.

A lightweight tool that automatically downloads and installs the latest version of **Discord** on Debian/Ubuntu-based Linux distributions (including Linux Mint).  
No more manual `.deb` downloads — keep Discord up-to-date with a single command.



## Features

Always fetches the latest Discord `.deb` package
Installs or updates Discord automatically
Works on **Ubuntu, Linux Mint, Pop!_OS, Debian**, and derivatives
Can be installed via a signed **APT repository**
Updates with sudo apt update.


## Installation

### Add the repository
```
curl -fsSL https://bobbycomet.github.io/Discordupdater/key.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/discord-updater.gpg

echo "deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/discord-updater.gpg] https://bobbycomet.github.io/Discordupdater/apt noble main" | sudo tee /etc/apt/sources.list.d/discord-updater.list
sudo apt update
```

```
sudo apt install discord-updater
```

```
discord-updater
```

This project is licensed under the MIT License.
Discord itself is a trademark of Discord Inc. This project is not affiliated with or endorsed by Discord.
