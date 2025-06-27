## Overview
This is a Discord bot that checks for when server members update their status. If the status matches a specified regex, it will assign the user a specified role and send a message to a specified channel. For example, users can add the server's vanity URL to their status and receive a role granting additional perks.

![image](https://github.com/user-attachments/assets/ec365174-19fb-446a-b25a-a9501768fc59) <br>
(automatically triggered message)

## Usage Instructions

1. Clone the respository and fill in the `config.js.sample` file with your own values. Rename it to `config.js`.
2. Fill out config.js as specified. Multiple guilds can be added as needed.
3. Install the dependencies and run:
```
npm i
node index.js
```
