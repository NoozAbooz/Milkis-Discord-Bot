## Overview
This is a Discord bot that checks for when server members update their status. If the status matches a specified regex, it will assign the user a specified role and send a message to a specified channel. For example, users can add the server's vanity URL to their status and receive a role granting additional perks.

## Usage Instructions

1. Clone the respository and fill in the `config.js.sample` file with your own values. Rename it to `config.js`.
2. Edit the statusRegex in `index.js` to match the status you want to check for.
2. Install the dependencies and run:
```
npm i
node index.js
```