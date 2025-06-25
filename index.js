require('dotenv').config();
const {
  Client,
  GatewayIntentBits,
  Partials,
  Events,
  ActivityType,
  EmbedBuilder
} = require('discord.js');

const TOKEN      = process.env.BOT_TOKEN;
const ROLE_ID    = process.env.ROLE_ID;
const CHANNEL_ID = process.env.CHANNEL_ID;

// case-insensitive regex
const statusRegex = /\.gg\/balls/i;

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

  if (process.env.HIDE_DEBUG === 'true') {
	console.log = function() {}
  }
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
    if (!customStatus) {
      if (member.roles.cache.has(ROLE_ID)) {
		console.log(`${newPresence.user.tag} status does not match regex → role removed`);
        await member.roles.remove(ROLE_ID);
      }
	  return;
	}

    // Test your regex
    if (statusRegex.test(customStatus)) {
      await member.roles.add(ROLE_ID);
	  console.log(`${newPresence.user.tag} set status to ${customStatus} → role added`);
      const channel = await client.channels.fetch(CHANNEL_ID);
    
	  if (channel.isTextBased()) {
      	// build your custom embed
      	const embed = new EmbedBuilder()
      	  .setColor(0xff9a8a)                    // pick your brand color
      	//   .setAuthor({
      	//     name: 'Milkis Jug',
      	//     iconURL: 'https://i.imgur.com/yourIcon.png'  // optional
      	//   })
      	  .setDescription([
      	    `thank you ${member} for repping MilkJug!`,
      	    `• we appreciate your support for us!`,
      	    `• since you're a supporter, we've given you <@&${ROLE_ID}> 🎁`,
      	    `• you'll now get link and pic perms! 🙏`
      	  ].join('\n'))
		  .setTimestamp()
		  .setFooter({ text: 'Add `.gg/balls` to your status to claim!' });

      	// send it
      	channel.send({ embeds: [embed] });
      }

	} else {
      // status failed the match ⇒ remove role if they have it
      if (member.roles.cache.has(ROLE_ID)) {
		console.log(`${newPresence.user.tag} status does not match regex → role removed`);
        await member.roles.remove(ROLE_ID);
      }
    }

  } catch (err) {
    console.error('Error in presenceUpdate handler:', err);
  }
});

client.login(TOKEN);
