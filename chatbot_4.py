
"""Simple inline keyboard bot with multiple CallbackQueryHandlers.

This Bot uses the Application class to handle the bot.
First, a few callback functions are defined as callback query handler. Then, those functions are
passed to the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot that uses inline keyboard that has multiple CallbackQueryHandlers arranged in a
ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line to stop the bot.
"""
import logging
import re
from enum import Enum
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
import contract_dbqueries
from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    filters,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    Updater,
    ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# User Input Types
class UserInputType(Enum):
    DATE = 1
    MONETARY = 2
    AMOUNT = 3


# Mapping of UserInputType and RegEx to check
userInputRegexMap = {
    UserInputType.DATE : "^(\d{2})\.(\d{2})\.(\d{4})$",
    UserInputType.MONETARY : "^(\d+,\d{2}|\d+)$",
    UserInputType.AMOUNT : "^\d+$"
}


# Stages
START, STARTALERTS, CHOOSE, CATEGORY, TYPE, CONTRACT, DETAILS, NEWCONTRACT, SETCATEGORY, SETRENEWALPERIOD, SETTYPE, SETBENEFICIARY, SETPERIOD, SETCONTRACTOR, SETSTARTDATE, SETENDDATE, SETNOTICEPERIOD, SETFEE, SETACCOUNT, SAVECONTRACT, REALLYDELETE, NEWCATEGORY, NEWTYPE, CONTRACT_ALERTING = range(24)
   
async def makeValidDateString(inputDate: str) -> str:
    """transforms a date input string into a valid date that can be saved in the database, e.g. 2024-12-31"""
    validDateString = inputDate
    regEx = userInputRegexMap[UserInputType.DATE]
    matches = re.search(regEx, inputDate)
    if (len(matches)> 0):
        validDateString = matches.group(3)+"-"+matches.group(2)+"-"+matches.group(1)
    return validDateString

async def startAlerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = []
    chat_id = update.effective_message.chat_id

    if (context.job_queue.get_jobs_by_name("Alerts-"+str(chat_id))):
        text = "Erinnerungen sind bereits aktiv."
        keyboard.append([InlineKeyboardButton("Erinnerungen deaktivieren!", callback_data="stopalerts")])
    else:
        text = "Möchtest du daran erinnert werden, Verträge zu kündigen?"
        keyboard.append([InlineKeyboardButton("Ja klar!", callback_data="startalerts")])
        keyboard.append([InlineKeyboardButton("Nein, doch nicht...", callback_data="end")])
   
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(text, reply_markup=reply_markup)
    return STARTALERTS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #print(str(update.message.from_user.id))
    if not (contract_dbqueries.isValidUser(context._user_id)):
        await update.message.reply_text("Sorry, du bist nicht berechtigt!")
        return ConversationHandler.END
        
    else:
        keyboard = []
        keyboard.append([InlineKeyboardButton("Vertrag anlegen", callback_data="newcontract"), InlineKeyboardButton("Vertrag anzeigen/bearbeiten", callback_data="showcontract")])
        keyboard.append([InlineKeyboardButton("Erinnerungen ein-/ausschalten", callback_data="alerts")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if (update.message):
            await update.message.reply_text("Ich bin dein Vertrags-Knecht. \U0001F916 Was kann ich für dich tun?", reply_markup=reply_markup)
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text("Ich bin dein Vertrags-Knecht. \U0001F916 Was kann ich für dich tun?", reply_markup=reply_markup)
        
        return CHOOSE
    

async def newcontract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = []
    categories = []
    categories = contract_dbqueries.getContractCategories()
    categoryCount = len(categories)
    for cid, c in enumerate(categories):
        if (cid % 2 == 0):
            if (cid == categoryCount-1):
                keyboard.append([InlineKeyboardButton(categories[cid][1], callback_data=categories[cid][0])])
            else:
                logger.info("at category ID: " +str(cid))
                keyboard.append([InlineKeyboardButton(categories[cid][1], callback_data=categories[cid][0]), InlineKeyboardButton(categories[cid+1][1], callback_data=categories[cid+1][0])])
    
    keyboard.append([InlineKeyboardButton("Neue Kategorie anlegen", callback_data="new_category")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    await query.edit_message_text("Gib eine Kategorie für den neuen Vertrag an:", reply_markup=reply_markup)
    return SETCATEGORY

async def alerting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:   
    """Alerting soll begonnen werden"""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_message.chat_id
    try:
        myhour = 7
        mytime = time(hour = myhour, minute = 20, second = 0)
    
        if (context.job_queue.get_jobs_by_name("Alerts-"+str(chat_id))):
            text = "Erinnerungen sind bereits aktiv."
        else:
            text = "Erinnerungen werden von jetzt an täglich um "+str(myhour+2)+" gesendet!"
            #context.job_queue.run_repeating(sendAlert, 10, first=5, last=None, data=None, name="Alerts", chat_id=chat_id, user_id=None, job_kwargs=None)
            context.job_queue.run_daily(sendAlert, mytime, chat_id=chat_id, name="Alerts-"+str(chat_id), job_kwargs=None)

        await update.effective_message.reply_text(text)
        return ConversationHandler.END

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Da ist was schiefgelaufen...")

async def stopAlerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:   
    """Alerting soll begonnen werden"""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_message.chat_id
    try:
           
        if (context.job_queue.get_jobs_by_name("Alerts-"+str(chat_id))):
            context.job_queue.get_jobs_by_name("Alerts-"+str(chat_id))[0].schedule_removal()
            text = "Erinnerungen wurden deaktiviert."
        else:
            text = "Es wurden keine Erinnerungen gefunden....das ist seltsam :/"
            

        await update.effective_message.reply_text(text)
        return ConversationHandler.END

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Da ist was schiefgelaufen...")

async def showcontract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Nutzer soll die Vertrags Kategorie wählen"""
    query = update.callback_query
    await query.answer()
    keyboard = []
    categories = []
    categories = contract_dbqueries.getActiveContractCategories()
    for c in categories:
        keyboard.append([InlineKeyboardButton(c[1], callback_data=c[0])])
    keyboard.append([InlineKeyboardButton("\U000025C0 zurück", callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Ich kann dich über deine laufenden Verträge informieren. Folgende Kategorien von Verträgen gibt es:", reply_markup=reply_markup)
    return CATEGORY

async def startover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = []
    categories = []
    categories = contract_dbqueries.getActiveContractCategories()

    for c in categories:
        keyboard.append([InlineKeyboardButton(c[1], callback_data=c[0])])
    keyboard.append([InlineKeyboardButton("zurück", callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Folgende Kategorien habe ich gefunden:", reply_markup=reply_markup)
    return CATEGORY

async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Die Vertragskategorie wurde gewählt, zeige nun die zugehörigen Vertragsarten an."""
    query = update.callback_query
    await query.answer()
    answer = query.data
    print("Kategorie: "+answer)
    keyboard = []
    types = []
    types = contract_dbqueries.getContractTypes(answer)
    for items in types:
        print(items)
    
    for t in types:
        keyboard.append([InlineKeyboardButton(t[1], callback_data=t[0])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Folgende Arten von Verträgen hast du:", reply_markup=reply_markup
    )
    return TYPE

async def setcategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Die Vertragskategorie wurde gewählt, zeige nun die zugehörigen Vertragsarten an."""
    query = update.callback_query
    await query.answer()
    answer = query.data
    context.user_data["category"] = answer
    keyboard = []
    types = []
    types = contract_dbqueries.getContractTypes(answer)
    
    for t in types:
        keyboard.append([InlineKeyboardButton(t[1], callback_data=t[0])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Um welche Art von Vertrag handelt es sich?", reply_markup=reply_markup
    )
    return SETTYPE

async def newcategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Neue Vertragskategorie soll angelegt werden."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Welche Kategorie möchtest du anlegen?"
    )
    return NEWCATEGORY

async def savecategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Neue Vertragskategorie soll gespeichert werden werden."""
    message = update.message
    newCategory = contract_dbqueries.newCategory(message.text)
    context.user_data["category"] = newCategory[0]
    logger.info("New Category saved: " +str(newCategory[0]) +" - "+message.text)
    await update.message.reply_text(
        text="Alles klar! Die Kategorie \"" + message.text + "\" wurde angelegt. Welche Vertragsart möchtest du zur neuen Kategorie anlegen?"
    )
    return NEWTYPE

async def savetype(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Neue Vertragsart soll gespeichert werden."""
    message = update.message
    newType = contract_dbqueries.newType(context.user_data["category"], message.text)
    context.user_data["type"] = newType[0]
    logger.info("New Type saved: " +str(newType) +" - "+message.text)
    keyboard = []
    beneficiaries = []
    beneficiaries = contract_dbqueries.getBeneficiaries()

    for t in beneficiaries:
        buttonlabel = str(t[0])
        keyboard.append([InlineKeyboardButton(buttonlabel, callback_data=t[1])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="Alles klar! Die Vertragsart \"" + message.text + "\" wurde angelegt.\nWer ist der Vertragsnehmer?" , reply_markup=reply_markup
    )
    return SETBENEFICIARY

async def type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Vertragsart wurde ausgewählt. Zeige nun die zugehörigen Verträge an"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    keyboard = []
    types = []
    contracts = contract_dbqueries.getContracts(answer)
    if (len(contracts) == 0 ):
        keyboard.append([InlineKeyboardButton("OK", callback_data=answer)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
        text="Für diese Vertragsart gibt es noch keine Verträge. Wähle eine andere Art.", reply_markup=reply_markup)
        return START

    for t in contracts:
        buttonlabel = str(t[18]) + " bei " + str(t[21])
        keyboard.append([InlineKeyboardButton(buttonlabel, callback_data=t[1])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Folgende Verträge habe ich gefunden:", reply_markup=reply_markup
    )
    return CONTRACT

async def settype(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Vertragsart wurde ausgewählt.Setze nun Vertragsnehmer"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    context.user_data["type"] = answer
    keyboard = []
    beneficiaries = []
    beneficiaries = contract_dbqueries.getBeneficiaries()

    for t in beneficiaries:
        buttonlabel = str(t[0])
        keyboard.append([InlineKeyboardButton(buttonlabel, callback_data=t[1])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Wer ist der Vertragsnehmer?", reply_markup=reply_markup
    )
    return SETBENEFICIARY

async def setbeneficiary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Vertragsnehmer wurde ausgewählt.Setze nun Anbieter"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    context.user_data["beneficiary"] = answer
    keyboard = []
    contractors = []
    contractors = contract_dbqueries.getContractors()
    for t in contractors:
        buttonlabel = str(t[1])
        keyboard.append([InlineKeyboardButton(buttonlabel, callback_data=t[0])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Wer ist der Anbieter?", reply_markup=reply_markup
    )
    return SETCONTRACTOR

async def setcontractor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Anbieter wurde ausgewählt.Setze nun Kosten"""
    update.callback_query
    query = update.callback_query
    await query.answer()
    answer = query.data
    context.user_data["contractor"] = answer
    
    await query.edit_message_text(
        text="Wie hoch sind die Kosten in €? Z.B. 12,99 (2 Dezimalstellen mit ,)"
    )
    return SETFEE


async def setfee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Kosten wurden gesetzt.Setze nun Zahlungsturnus"""
    message = update.message
   
    context.user_data["fee"] = message.text
    keyboard = []
    periods = []
    periods = contract_dbqueries.getPeriods()
    for t in periods:
        buttonlabel = str(t[0])
        keyboard.append([InlineKeyboardButton(buttonlabel, callback_data=t[1])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="In welchem Turnus bezahlst du?", reply_markup=reply_markup
    )
    return SETACCOUNT

async def setfeeAgain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """given format of fee was not valid"""
    await update.effective_user.send_chat_action("typing")
    await update.message.reply_text(
            text="Das verstehe ich leider nicht \U00002639."
        )
    await update.message.reply_text(
            text="Bitte gib die Kosten für den Vertrag in € an. Falls nötig, nutze dafür ein Komma und zwei Dezimalstellen, z.B.: 12,99"
        )
    return SETFEE

async def setaccount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Zahlungsturnus wurde gesetzt.Setze nun Kontoverbindung"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    context.user_data["period"] = answer
    keyboard = []
    accounts = []
    accounts = contract_dbqueries.getAccounts()
    for t in accounts:
        buttonlabel = str(t[1])
        keyboard.append([InlineKeyboardButton(buttonlabel, callback_data=t[0])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Bitte gib das Konto für die Zahlung an!", reply_markup=reply_markup
    )
    return SETNOTICEPERIOD

async def setnoticeperiod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Konto wurde gesetzt.Setze nun Kündigungsfrist"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    context.user_data["account"] = answer
    
    await query.edit_message_text(
        text="Wieviele Monate beträgt die Kündigungsfrist?"
    )
    
    return SETRENEWALPERIOD

async def setrenewalperiod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Setze nun Verlängerungszeitraum"""
    message = update.message
    context.user_data["noticeperiod"] = message.text
    
    await update.message.reply_text(
        text="Wieviele Monate beträgt die automatische Vertragsverlängerung?"
    )
    
    return SETSTARTDATE

async def setstartdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    context.user_data["renewalperiod"] = message.text
    
    await update.message.reply_text(
        text="Wann war/ist der Beginn des Vertrags? z.B. 01.01.2024"
    )
    return SETENDDATE

async def setEndDate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    context.user_data["startdate"] = makeValidDateString(message.text)
    await update.message.reply_text(
        text="Wann ist das Ende des Vertrags? z.B. 31.12.2024"
    )
    return SAVECONTRACT

async def setEndDateAgain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        text="Diese Angabe verstehe ich leider nicht \U00002639. Bitte gib den Vertragsbeginn als Dataum an z.B. 31.12.2024"
    )
    return SETENDDATE

async def saveContract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    context.user_data["enddate"] = makeValidDateString(message.text)
    enddate = datetime.strptime(context.user_data["enddate"], '%Y-%m-%d').date()
    nextcanceldate = enddate - relativedelta(months=+int(context.user_data["noticeperiod"])) 
    context.user_data["nextcancellationdate"] = nextcanceldate
    context.user_data["userid"] = context._user_id
    newContract = contract_dbqueries.saveContract(context.user_data)
    for x in newContract:
        print(x)
    context.user_data["last_inserted_contract"] = newContract[0]

    keyboard = []
    keyboard.append([InlineKeyboardButton("ja", callback_data="activate_alerting")])
    keyboard.append([InlineKeyboardButton("nein", callback_data="end_conversation")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="Möchtest du den Vertragswecker für diesen Vertrag aktivieren?", reply_markup=reply_markup
    )

    return CONTRACT_ALERTING

async def saveContractAgain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        text="Diese Angabe verstehe ich leider nicht \U00002639. Bitte gib das Vertragsende als Dataum an z.B. 31.12.2024"
    )
    SAVECONTRACT

async def activateContractAlerting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if (query.data == "activate_alerting"):
        contract_dbqueries.setContractAlertingStatus(context.user_data["last_inserted_contract"], 1)
        await query.edit_message_text(
            text="Super, der Vertragswecker wurde aktiviert \U0001F44D. Du wirst rechtzeitig von mir informiert, sobald dein Vertrag ausläuft. Bis später!"
        )
    
    else:
        await query.edit_message_text(
            text="Alles klar, bis später \U0001F44B."
        )

    return ConversationHandler.END

async def contract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Zeige die Vertragsdetails für einen spezifischen Vertrag"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    keyboard = []
    keyboard.append([InlineKeyboardButton("OK, Danke!", callback_data="end")])
    keyboard.append([InlineKeyboardButton("Vertrag löschen", callback_data="delete-"+str(answer))])
    
    contract = contract_dbqueries.getContractById(int(answer))
    for items in contract:
            print(items)
    today = datetime.now().date()
    canceldate = contract[7]
    delta =  canceldate - today
    daystocancel = str(delta.days)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Folgende Infos gibt es zum Vertrag:\n"
                                            +"\n *Typ:* "+str(contract[5])+"\n"
                                            +"\n *Kosten:* "+str(contract[1])+"€"+"\n"
                                            +"\n *Für:* "+str(contract[2])+"\n"
                                            +"\n *Anbieter:* "+str(contract[4])+"\n"
                                            +"\n *Zahlung:* "+str(contract[3])+"\n"
                                            +"\n *Kündigung bis:* "+str(contract[7])+" (noch "+daystocancel+" Tage!)"+"\n"
                                            +"\n *Konto:* "+str(contract[6]), reply_markup=reply_markup, parse_mode= 'Markdown'
    )
    return DETAILS

async def deleteContract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lösche einen spezifischen Vertrag (Mit DOI)"""
    query = update.callback_query
    await query.answer()
    answer = query.data
    keyboard = []
    id = answer[answer.find('-')+1:]
    print(id)
    keyboard.append([InlineKeyboardButton("Ja, löschen!", callback_data=id)])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Bist du sicher?", reply_markup=reply_markup
    )
    return REALLYDELETE

async def reallyDeleteContract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    answer = query.data
    keyboard = []
    keyboard.append([InlineKeyboardButton("OK, Danke!", callback_data="end")])

    contract_dbqueries.deleteContractById(int(answer))
    await query.edit_message_text(
        text="Vertrag wurde gelöscht.\n Bis später!"
    )

    return ConversationHandler.END

async def editcontract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""
   
    query = update.callback_query
    await query.answer()
    answer = query.data
    keyboard = []
    keyboard.append([InlineKeyboardButton("OK", callback_data="end")])
    types = []
    
    
    contract = contract_dbqueries.getContractById(int(answer))
   
   
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Folgende Infos gibt es zum Vertrag:", reply_markup=reply_markup
    )
    return ConversationHandler.END

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Alles klar, bis später!")
    return ConversationHandler.END

async def sendAlert(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sende den Alert."""
    job = context.job
    today = datetime.now().date()
    contracts = contract_dbqueries.getAllContracts()
    for c in contracts:
        canceldate = c[6]
        delta = canceldate - today
        if (delta.days <= 14):
            await context.bot.send_message(job.chat_id, parse_mode= 'Markdown', text=f"Dies ist eine Erinnerung!\nDein Vertrag: *"+str(c[17])+"* bei "+str(c[20])+" verlängert sich in "+str(delta.days)+" Tag(en) automatisch um "+str(c[15])+" Monat(e).\nVergiss nicht, zu kündigen!")

    
async def validateUserInput(input: str, inputType : UserInputType) -> bool:
    """validate user input based on input type provided."""
    regEx = userInputRegexMap[inputType]
    matches = re.findall(regEx, input)
    if (len(matches)> 0):
        return True
    else:
        return False


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("5639687161:AAFg8NO8kOcHQmFODEKA8SZSshQv4fiqQHg").build()
  
    conv_handler = ConversationHandler(
        entry_points=
            [CommandHandler("start", start)],
            
            
        states={
            START: [
                CallbackQueryHandler(startover, pattern="^.+$") 
            ],
            STARTALERTS: [
                CallbackQueryHandler(alerting, pattern="^startalerts$"),
                CallbackQueryHandler(end, pattern="^end$"),
                CallbackQueryHandler(stopAlerts, pattern="^stopalerts$")
            ],
            CHOOSE: [
                CallbackQueryHandler(newcontract, pattern="^newcontract$"),
                CallbackQueryHandler(showcontract, pattern="^showcontract$"),
                CallbackQueryHandler(startAlerts, pattern="^alerts$")
            ],
            CATEGORY: [
                CallbackQueryHandler(start, pattern="^back$"),
                CallbackQueryHandler(category, pattern="^.+$")
                
            ],
            SETCATEGORY: [
                CallbackQueryHandler(newcategory, pattern="^new_category$"),
                CallbackQueryHandler(setcategory, pattern="^.+$")                
            ],
            NEWCATEGORY: [
                MessageHandler(filters.Regex("^.+$"), savecategory)
            ],
            NEWTYPE: [
                MessageHandler(filters.Regex("^.+$"), savetype)
            ],
            TYPE: [
                CallbackQueryHandler(type, pattern="^.+$")
            ],
            SETTYPE: [
                CallbackQueryHandler(settype, pattern="^.+$")
            ],
            SETBENEFICIARY: [
                CallbackQueryHandler(setbeneficiary, pattern="^.+$")
            ],
            SETCONTRACTOR: [
                CallbackQueryHandler(setcontractor, pattern="^.+$"),
                MessageHandler(filters.Regex("^$"), setfee)
            ],
            SETFEE: [
                MessageHandler(filters.Regex(userInputRegexMap[UserInputType.MONETARY]), setfee),
                MessageHandler(filters.Regex("^.+$"), setfeeAgain)
            ],
            SETNOTICEPERIOD: [
                CallbackQueryHandler(setnoticeperiod, pattern="^.+$")
            ],
            SETRENEWALPERIOD: [
                MessageHandler(filters.Regex("^.+$"), setrenewalperiod)
            ],
            SETSTARTDATE: [
                MessageHandler(filters.Regex("^.+$"), setstartdate)

            ],
            SETENDDATE: [
                MessageHandler(filters.Regex("^\d{4}-\d{2}-\d{2}$"), setEndDate),
                MessageHandler(filters.Regex("^\d{2}\.\d{2}\.\d{4}$"), setEndDate),
                MessageHandler(filters.Regex("^.*$"), setEndDateAgain)
            ],
            SAVECONTRACT: [
                MessageHandler(filters.Regex("^\d{4}-\d{2}-\d{2}$"), saveContract),
                MessageHandler(filters.Regex("^\d{2}\.\d{2}\.\d{4}$"), saveContract),
                MessageHandler(filters.Regex("^.*$"), saveContractAgain)
            ],
            SETACCOUNT: [
                CallbackQueryHandler(setaccount, pattern="^.+$")
            ],
            CONTRACT: [
                CallbackQueryHandler(contract, pattern="^.+$")
            ],
            REALLYDELETE: [
                CallbackQueryHandler(reallyDeleteContract, pattern="^.+$")
            ],
            CONTRACT_ALERTING: [
                CallbackQueryHandler(activateContractAlerting, pattern="^.+$")
            ],
            DETAILS: [
                CallbackQueryHandler(end, pattern="^end$"),
                CallbackQueryHandler(editcontract, pattern="^edit$"),
                CallbackQueryHandler(deleteContract, pattern="^.+$")

            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()