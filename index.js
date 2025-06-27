const {
  Client,
  GatewayIntentBits,
  Partials,
  Events,
  ActivityType,
  EmbedBuilder
} = require('discord.js');

const guildConfig = require('./config.js');

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

    // fetch this guild's config
    const cfg = guildConfig[newPresence.guild.id];
    if (!cfg) return;            // not configured, skip

    const { roleId, channelId, targetRegex, vanityText } = cfg;

    // Get *only* the custom-status text
    const customStatus = newPresence.activities
      .find(a => a.type === ActivityType.Custom)
      ?.state;

    // If there's no custom status, remove role (likely went invis)
    if (!customStatus) {
      if (member.roles.cache.has(roleId)) {
		    console.log(`${newPresence.user.tag} status missing (likely invis) → role removed`);
        await member.roles.remove(roleId);
      }
	    return;
	  }

    // Test your regex
    if (targetRegex.test(customStatus)) {
      await member.roles.add(roleId);
	    console.log(`${newPresence.user.tag} set status to ${customStatus} → role added`);
      const channel = await client.channels.fetch(channelId);
    
      // build your custom embed
      const embed = new EmbedBuilder()
        .setColor(0xff9a8a)                    // pick your brand color
      //   .setAuthor({
      //     name: 'Milkis Jug',
      //     iconURL: 'https://i.imgur.com/yourIcon.png'  // optional
      //   })
        .setDescription([
          `thank you ${member} for repping us!`,
          `• we appreciate your support for us! 😍`,
    	    `• since you're a supporter, we've given you <@&${ROLE_ID}> 🎁`,
    	    `• you'll now get link and pic perms & 20s+ ct! 🔗🖼️ `
    	  ].join('\n'))
		    .setTimestamp()
		    .setFooter({ text: `Want this too? Add ${vanityText} to your status to claim!` });

      // send it
      channel.send({ embeds: [embed] });

	  } else {
      // status failed the match ⇒ remove role if they have it
      if (member.roles.cache.has(roleId)) {
		    console.log(`${newPresence.user.tag} status does not match regex → role removed`);
        await member.roles.remove(roleId);
      }
    }

  } catch (err) {
    console.error('Error in presenceUpdate handler:', err);
  }
});

client.login(BOT_TOKEN);
