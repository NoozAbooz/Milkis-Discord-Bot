// index.js (CommonJS version)
require('dotenv').config();
const {
  Client,
  GatewayIntentBits,
  Partials,
  Events,
  ActivityType
} = require('discord.js');

const TOKEN      = process.env.BOT_TOKEN;
const ROLE_ID    = process.env.ROLE_ID;
const CHANNEL_ID = process.env.CHANNEL_ID;

const statusRegex = process.env.STATUS_REGEX

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildPresences,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages
  ],
  partials: [Partials.Channel]
});

client.once(Events.ClientReady, () => {
  console.log(`Logged in as ${client.user.tag}`);
});

client.on(Events.PresenceUpdate, async (_, newPresence) => {
  try {
    const member = newPresence.member;
    if (!member) return;

    // Get *only* the custom-status text
    const customStatus = newPresence.activities
      .find(a => a.type === ActivityType.Custom)
      ?.state;

    // If there's no custom status, bail out
    if (!customStatus) return;

	console.log(`${newPresence.user.tag} updated their status: ${customStatus}`);

    // Test your regex
    if (statusRegex.test(customStatus)) {
      await member.roles.add(ROLE_ID);
      const channel = await client.channels.fetch(CHANNEL_ID);
      if (channel.isTextBased()) {
        channel.send(
          `${member.user} just set their custom status to "${customStatus}" and has been given the role!`
        );
      }
    }
  } catch (err) {
    console.error('Error in presenceUpdate handler:', err);
  }
});

client.login(TOKEN);
