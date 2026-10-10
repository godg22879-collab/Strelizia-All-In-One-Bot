import discord 
from discord .ext import commands 
from discord import app_commands ,Interaction 
from core import Context 
from core .Strelizia import Strelizia 
from core .Cog import Cog 
from utils .Tools import getConfig ,ignore_check ,blacklist_check 
from utils import help as vhelp 
import asyncio 

color =0x000000 

class HelpSlash (Cog ,name ="helpslash"):
    def __init__ (self ,client :Strelizia ):
        self .bot =client 

    def create_strelizia_mapping (self ,mapping ):
        """Create a filtered mapping that only includes cogs from cogs/strelizia directories"""
        strelizia_mapping ={}


        allowed_cog_classes ={

        '_general','_voice','_games','_welcome','ticket','__sticky','__boost',
        '_automod','_antinuke','_music','_extra','_fun','_moderation','_giveaway',

        '_leveling','_ai','_server','RoleplayHelp','VerificationHelp',
        '_tracking','_logging','_counting','_Backup','_crew','_ignore','eco','_bypass'
        }

        for cog ,commands in mapping .items ():
            if cog and hasattr (cog ,'__class__'):
                cog_class_name =cog .__class__ .__name__ 

                if cog_class_name in allowed_cog_classes and hasattr (cog ,'help_custom'):
                    strelizia_mapping [cog ]=commands 

        return strelizia_mapping 

    @app_commands .command (name ="help",description ="Shows help about the bot and commands")
    async def help_slash (self ,interaction :Interaction ):
        """Slash command version of help - shows main help menu"""
        try :

            if interaction .guild :
                data =await getConfig (interaction .guild .id )
                prefix =data ["prefix"]
            else :
                prefix =">"


            await interaction .response .defer ()


            mapping ={}
            for cog in interaction .client .cogs .values ():
                if hasattr (cog ,'get_commands')and cog .get_commands ():
                    mapping [cog ]=cog .get_commands ()

            await asyncio .sleep (0.1 )


            embed =discord .Embed (
            title ="𝐇𝐞𝐥𝐩 𝐌𝐞𝐧𝐮",
            color =0x000000 
            )
            d4hz_path = os.path.abspath("D4Hz.gif") if os.path.exists("D4Hz.gif") else (os.path.abspath("../D4Hz.gif") if os.path.exists("../D4Hz.gif") else None)
            d4hz_file = discord.File(d4hz_path, filename="D4Hz.gif") if d4hz_path else None
            if d4hz_file:
                embed.set_image(url="attachment://D4Hz.gif")
            else:
                embed.set_image(url="https://cdn.discordapp.com/banners/1372468860435042344/2200c89d12a45d8cf648694ad30535f8.png?size=512")

            embed .add_field (
            name ="<:help:1388729258263969903> __**𝐆𝐞𝐧𝐞𝐫𝐚𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬**__",
            value =">>> \n <a:vcwaiting:1523295680875987045> 𝐕𝐨𝐢𝐜𝐞\n"
            " <:heads:1385235448003039273> 𝐆𝐚𝐦𝐞𝐬\n"
            " <:join_icon:1374287302934790235> 𝐖𝐞𝐥𝐜𝐨𝐦𝐞𝐫\n"
            " <a:thread1:1523295595689934888> 𝐓𝐢𝐜𝐤𝐞𝐭𝐢𝐧𝐠\n"
            " <:icon_edit:1372531753343778908> 𝐀𝐮𝐭𝐨 𝐒𝐞𝐭𝐮𝐩\n"
            " <:icon_autorole:1372532056344625213> 𝐀𝐮𝐭𝐨𝐫𝐨𝐥𝐞\n"
            " <:fun:1373621697776975962> 𝐅𝐮𝐧\n"
            " <:icon_ignore:1373173575078379590> 𝐈𝐠𝐧𝐨𝐫𝐞 𝐂𝐡𝐚𝐧𝐧𝐞𝐥𝐬\n"
            " <:logging_icons:1377373741268471900> 𝐋𝐨𝐠𝐠𝐢𝐧𝐠\n"
            " <:plus_icons:1377949309751791717> 𝐂𝐨𝐮𝐧𝐭𝐢𝐧𝐠\n"
            " <:leveling_icons:1378293065273442395> 𝐋𝐞𝐯𝐞𝐥𝐢𝐧𝐠\n"
            " <:tracking_icons:1378293093219962921> 𝐓𝐫𝐚𝐜𝐤𝐢𝐧𝐠\n"
            )

            embed .add_field (
            name ="<:strelizia_owner:1374273169086484480> __**𝐁𝐨𝐭 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬**__",
            value =">>> \n <:admin:1373949463814738002> 𝐒𝐞𝐜𝐮𝐫𝐢𝐭𝐲\n"
            " <:Automod:1374274713865687120> 𝐀𝐮𝐭𝐨𝐦𝐨𝐝\n"
            " <:icons_channel:1381865641463517325> 𝐔𝐭𝐢𝐥𝐢𝐭𝐲\n"
            " <:music:1373174130907807814> 𝐌𝐮𝐬𝐢𝐜\n"
            " <a:ban:1376600344502468618> 𝐌𝐨𝐝𝐞𝐫𝐚𝐭𝐢𝐨𝐧\n"
            " <:icon_categories:1373173618858659901> 𝐆𝐞𝐧𝐞𝐫𝐚𝐥\n"
            " <:Giveaway:1373566437104554047> 𝐆𝐢𝐯𝐞𝐚𝐰𝐚𝐲\n"
            " <:Ai:1375898214087135263> 𝐀𝐫𝐭𝐢𝐟𝐢𝐜𝐢𝐚𝐥 𝐈𝐧𝐭𝐞𝐥𝐥𝐢𝐠𝐞𝐧𝐜𝐞\n"
            " <:backup_icons:1376857941986250844> 𝐁𝐚𝐜𝐤𝐮𝐩\n"
            " <:icons_tv:1381541359055540255> 𝐑𝐨𝐥𝐞play\n"
            " <:staff_icons:1381539824711766046> 𝐒𝐭𝐚𝐟𝐟 𝐀𝐩𝐩𝐥𝐢𝐜𝐚𝐭𝐢𝐨𝐧\n"
            " <:icon_autorole:1372532056344625213> 𝐁𝐲𝐩𝐚𝐬𝐬 𝐑𝐨𝐥𝐞𝐬\n"
            )

            embed .set_footer (
            text =f"𝐑𝐞𝐪𝐮𝐞𝐬𝐭𝐞𝐝 𝐁𝐲 {interaction.user}",
            )

            embed .set_thumbnail (url =interaction .user .avatar .url if interaction .user .avatar else interaction .user .default_avatar .url )


            class FakeContext :
                def __init__ (self ,interaction ):
                    self .author =interaction .user 
                    self .guild =interaction .guild 
                    self .bot =interaction .client 
                    self .prefix ="/"
                    self .interaction =interaction 

            fake_ctx =FakeContext (interaction )


            mapping ={}
            for cog in self .bot .cogs .values ():
                if cog .get_commands ():
                    mapping [cog ]=cog .get_commands ()


            filtered_mapping =self .create_strelizia_mapping (mapping )


            view =vhelp .View (mapping =filtered_mapping ,
            ctx =fake_ctx ,
            homeembed =embed ,
            ui =2 )


            if d4hz_file :
                await interaction .edit_original_response (embed =embed ,view =view ,attachments =[d4hz_file ])
            else :
                await interaction .edit_original_response (embed =embed ,view =view )

        except Exception as e :
            print (f"Error in slash help command: {e}")
            if not interaction .response .is_done ():
                await interaction .response .send_message (f"An error occurred: {str(e)}",ephemeral =True )
            else :
                await interaction .followup .send (f"An error occurred: {str(e)}",ephemeral =True )

async def setup (client ):
    await client .add_cog (HelpSlash (client ))

"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""

"""
: ! Aegis !
    + Discord: root.exe
    + Community: https://discord.gg/meet (AeroX Development )
    + for any queries reach out Community or DM me.
"""