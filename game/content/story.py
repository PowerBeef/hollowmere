# SPDX-License-Identifier: MIT
"""All fixed text in Hollowmere. Order matters for ranges (STR_X_0 .. n), and
for saves: a save keeps its objective as a string's number, so text added in a
later version goes in LATE, which is numbered after everything else."""

INTRO = [
    "Autumn, 1958.\n\nWhen my brother Thomas coughed blood at the dinner table, "
    "the doctors sent him north, to Hollowmere: the Ashby family's house on an island in a cold, black lake. "
    "Dr. Ashby took a few consumptives there, privately. Clean air, he promised. Rest. The water cure.",

    "His letters came every week. Then every month. They grew shorter.\n\n"
    "The last one arrived in March. It said only:\n\n"
    "'Evie. Don't let them take me down to the water.'",

    "In September a solicitor wrote that Dr. Ashby had closed the house and sent his patients south.\n\n"
    "Thomas never arrived.\n\nNo one would tell me why.",

    "So tonight I borrowed a rowboat and a flashlight, and I crossed the lake alone.\n\n"
    "The house was dark.\n\nAll but one window, high up under the roof.",
]

ENDING = [
    "The lantern was cold in my hands, colder than the lake.\n\n"
    "Behind me the Sister folded down into the dark like a dropped sheet. When I dared to look, "
    "there was only black water spreading across the chapel boards, and the smell of the mere.",

    "I found Thomas in the cupola above the chapel, curled against the little bell, thin as a winter branch.\n\n"
    "He opened his eyes and said my name, and I could have wept at the sound of it.",

    "We rowed away as the sky turned grey. Neither of us looked back.\n\n"
    "Behind us, high up under the roof of the house, one window still burned.\n\n"
    "I never asked him what he heard in the pipes.",
]

ENDING_TRUE = ("Years later, after Thomas married and moved west, he mailed me a photograph of his daughter.\n\n"
               "She was holding a little music box.\n\n"
               "On the back he had written: 'She hums a song in her sleep. We never taught it to her.'")

CREDITS = ("HOLLOWMERE\n\n\nA horror game for the Game Boy Advance\n\n\n"
           "Directed by\n\nPowerBeef\n\n\n"
           "Design, programming, art, sound,\nmusic and story\n\nClaude\n(Anthropic)\n\n\n"
           "Engine\nThin-wall raycaster with see-through\ndoorways, textured 3D furniture,\n"
           "per-room materials, dynamic lighting,\nstereo positional audio and hardware\n"
           "display effects, in C and\nhand-written ARM assembly.\n\n"
           "Every texture, model, sprite, sound\nand note of music was generated\nprocedurally for this game.\n\n\n"
           "Thank you for playing.\n\n\n\nWhatever you do,\nkeep your light low.")

CHAPTERS = ["The House", "Beneath", "The Wards", "The Chapel"]
CHNUMS = ["I", "II", "III", "IV"]

NOTE_TITLES = [
    "Housekeeper's Ledger",
    "Letter to Evie (unsent)",
    "Note in the Butler's Chest",
    "The Gardener's Scrawl",
    "Generator Room Notice",
    "Thomas's Notebook, p. 12",
    "Dr. Ashby: Clinical Notes",
    "Sister Hollis's Diary",
    "A Child's Drawing",
    "Ashby's Journal, Final Entry",
    "Thomas, to Evie",
    "Scratched into the Boards",
]

NOTES = [
    # 0
    "Sept 14. The last boat left at six with the doctor and the cook. Sister Hollis would not board. "
    "Says her patients are not finished.\n\n"
    "Sept 15. Every lamp in the house out except the one under the roof, and every fire: she cannot pass a lit "
    "hearth, she must kneel to it until it is cold. Heard her singing on the back stair "
    "around two. That tune again. She goes down to the cellar every night now, so I have taken the cellar key "
    "off the board and shut it in the hall clock. She stopped that clock the night she came up out of the water. "
    "She will not go near it.\n\n"
    "Sept 16. I go on the supply boat. Whoever reads this: do not walk this house after dark with a lamp lit. "
    "She follows the light. - M. Brandt, Housekeeper",
    # 1
    "Dear Evie,\n\nThey say I'm improving. I'm not. The cough is worse, but the night sister "
    "says not to worry, the water will take it.\n\n"
    "Every night she does her rounds with that lantern. She stops at each bed and counts us, "
    "and her lips move like she's praying. Last night she stopped at Peter's bed. "
    "In the morning he was gone.\n\n"
    "I'm done writing what they want to read. Maybe that's why my letters stopped reaching you.\n\n"
    "Your brother,\nTom",
    # 2
    "To whoever is left in this house:\n\n"
    "When you see her lantern, put out your own light. She sees no better in the dark than we do, "
    "but she sees a lamp from the far end of any corridor.\n\n"
    "If she comes for you, do not stand there and pray. Run. Get behind a door, or into a wardrobe, "
    "and hold your breath until her steps are gone.\n\n"
    "She hears running. She hears doors. Walk softly.\n\n- R. Pell, Butler",
    # 3
    "Main stair went in August, the whole upper flight, like something pulled it down from underneath. "
    "Only way upstairs now is the service lift, and that's dead since the spring flooded the generator.\n\n"
    "Spare fuses are all over down here: wine cellar, boiler room, the cold room.\n\n"
    "Boiler room key's in the laundry.\n\n"
    "I'm not going back down there. Not with her.",
    # 4
    "GENERATOR ROOM - NOTICE\n\n"
    "Unit requires three (3) 30-amp cartridge fuses. Spares were scattered when the spring came up "
    "through the floor. Check the wine cellar, the boiler room and the cold room.\n\n"
    "Fit all three into the fuse panel, then pull the start lever.\n\n"
    "The service lift will NOT run on fewer than three.",
    # 5
    "They brought Peter back up from the cellar. He doesn't cough anymore. He doesn't do anything "
    "anymore. He sits on the edge of his bed and listens to the pipes like they're talking to him.\n\n"
    "When I said his name he smiled with only half of his face.\n\n"
    "Afterwards the night sister held my hand and said, 'You'll go down soon, Thomas. "
    "Isn't that wonderful.'",
    # 6
    "THE MERE CURE. Patients are immersed in the spring beneath the house for up to ninety seconds.\n\n"
    "Results remarkable. In 31 of 34 cases no trace of tuberculosis remained.\n\n"
    "Side effects: profound apathy. Loss of appetite. Nocturnal wandering toward the cellar stair. "
    "Patients describe 'something taking the sickness out with the breath.'\n\n"
    "The family need not be troubled with the side effects.",
    # 7
    "The Doctor says the water heals them. I believe him. I must believe him.\n\n"
    "I carry the lamp down so they are not afraid of the dark. I hold their hands while they go "
    "under, and I count. One. Two. Three. Some of them come back up. I count them too.\n\n"
    "Last night, when I counted, the water counted back.",
    # 8
    "(A crayon drawing of a very tall lady holding a lantern. Underneath, in careful letters:)\n\n"
    "The night lady sings us the box song so we can sleep. She says when I am all better I can "
    "go swimming under the house with the others. Her face hurts so she wears the bandages.\n\n"
    "I am not scared of her.\n\nI am a little scared of her.",
    # 9
    "August. The spring rose and flooded the cellars. Sister Hollis went down with her lantern to bring "
    "the patients up. She was under for an hour. An hour.\n\n"
    "When she came up she was still holding the lantern. She has not put it down since.\n\n"
    "She does her rounds. She takes them down to the water, one by one, and now they do not come "
    "back at all.\n\n"
    "I am leaving tonight. God forgive me, I have told no one what lives in that water. "
    "The attic key stays in this desk. Let it rust here.",
    # 10
    "Evie,\n\nIf you're reading this, you came anyway. Stupid, brave Evie.\n\n"
    "She's taking me down tonight. I'll slip away if I can and hide up in the attic. "
    "She doesn't climb the ladder in the cupola. I've watched her.\n\n"
    "Listen. It's the lantern. Her light is what leads them down. Without it she's as lost in the "
    "dark as the rest of us. Take it from her if you can. Come up behind her, quiet, no light.\n\n"
    "The attic key is in Ashby's study.\n\n- Tom",
    # 11
    "CUPOLA\n\nNOT THE WATER\n\nDON'T LOOK AT THE WATER\n\n- T.M.",
]

KEYS = ["", "Cellar Key", "Boiler Room Key", "Suite Key", "Attic Key", "", "", "Box of Matches"]
KEY_MATCHES = 7      # (not a key, but kept like one: what the hearths are lit with, found again on each floor)
LOCK_HINTS = ["Locked.", "Locked. CELLAR.", "BOILER ROOM - KEEP SHUT. Chalked below it: KEY ON THE LAUNDRY TABLE.",
              "Locked. A brass plate: DR. L. ASHBY.", "Locked. The attic.",
              "Locked.", "Locked.", "Locked."]
DEATHS = ["She found you.", "She counted you.", "Another one for the water.", "The lantern always finds you."]

FIXED = [
    ('NONE', ''),
    ('SPLASH_0', "HOLLOWMERE"),
    ('SPLASH_1', "Best played in the dark,"),
    ('SPLASH_2', "with headphones."),
    ('P_BATTERY', "\x01 Take battery"),
    ('P_FUSE', "\x01 Take fuse"),
    ('P_KEY', "\x01 Take key"),
    ('P_NOTE', "\x01 Read note"),
    ('P_TAKE', "\x01 Take"),
    ('P_OPEN', "\x01 Open"),
    ('P_CLOSE', "\x01 Close"),
    ('P_HIDE', "\x01 Hide"),
    ('P_FUSEBOX', "\x01 Fuse panel"),
    ('P_GENERATOR', "\x01 Start lever"),
    ('P_EXIT', "\x01 Go"),
    ('P_EXAMINE', "\x01 Examine"),
    ('P_LANTERN', "\x01 Take the lantern"),
    ('P_LEAVE', "\x01 Step out"),
    ('M_BATTERY', "A fresh battery. The beam steadies."),
    ('M_FUSE1', "A 30-amp fuse. (1 of 3)"),
    ('M_FUSE2', "Another fuse. (2 of 3)"),
    ('M_FUSE3', "That makes three fuses."),
    ('M_TOOK', "Took the "),
    ('M_UNLOCKED', "Unlocked with the "),
    ('M_STUCK', "It won't budge."),
    ('M_DEADBATT', "The flashlight is dead."),
    ('M_STIRRING', "She's stirring. Keep still, in the dark."),
    ('UI_PAUSED', "PAUSED"),
    ('UI_RESUME', "Resume"),
    ('UI_JOURNAL', "Journal"),
    ('UI_MAP', "Map"),
    ('MAP_ITEMS', "Items left"), ('MAP_CLEAR', "Cleared"), ('MAP_LOCKED', "Locked"), ('MAP_YOU', "You"),
    ('MAP_UNKNOWN', "Unexplored"),
    ('UI_OPTIONS', "Options"),
    ('UI_QUIT', "Quit to title"),
    ('UI_NOOBJ', "..."),
    ('UI_BATTERY', "Battery "),
    ('UI_FUSES', "Fuses "),
    ('UI_FOUND', "Found "),
    ('UI_CONTINUE', "\x01  Try again"),
    ('UI_NOTES', "Notes found: "),
    ('UI_DEATHS', "Deaths: "),
    ('UI_TIME', "Time: "),
    ('UI_THEEND', "THE END"),
    ('ENDING_TRUE', ENDING_TRUE),
    ('CTRL_TITLE', "HOW TO SURVIVE"),
    ('CTRL_K0', "D-PAD"), ('CTRL_V0', "Walk / turn"),
    ('CTRL_K1', "L / R"), ('CTRL_V1', "Step sideways"),
    ('CTRL_K2', "A"), ('CTRL_V2', "Open, take, read, hide"),
    ('CTRL_K3', "START"), ('CTRL_V3', "Pause, map, journal, options"),
    ('CTRL_K4', "B (hold)"), ('CTRL_K4B', "R (hold)"), ('CTRL_V4', "Run - she hears it"),
    ('CTRL_K5', "SELECT"), ('CTRL_K5B', "B"), ('CTRL_V5', "Flashlight on / off"),
    ('CTRL_K7', "SELECT (hold)"), ('CTRL_K7B', "SELECT"), ('CTRL_V7', "Map"),
    ('CTRL_K6', "DARKNESS"), ('CTRL_V6', "Keep still and she may pass"),
    ('CTRL_TIP', "She is drawn to light and noise.\nWardrobes hide you, if she does not see."),
    ('CREDITS', CREDITS),
]


# Text added since v1.2: numbered after the levels' own strings, so that the
# numbers v1.2 gave (a save holds its objective's) still mean the same text.
LATE = [
    ('P_LIGHT', "\x01 Light the fire"),
    ('P_SMOTHER', "\x01 Put out the fire"),
    ('M_FIRE_LIT', "The kindling takes. She will not leave a fire burning."),
    ('M_FIRE_NOMATCH', "Logs and kindling, laid ready. I have nothing to light them with."),
    ('M_FIRE_DEAD', "Raked out and cold. It won't take again."),
    ('M_FIRE_OUT', "I rake the logs apart. The fire sinks."),
]


def late_strings():
    return list(LATE)


def string_list():
    """Returns list of (name, text) with contiguous ranges."""
    out = list(FIXED)
    for i, t in enumerate(INTRO):
        out.append((f'INTRO_{i}', t))
    for i, t in enumerate(ENDING):
        out.append((f'ENDING_{i}', t))
    for i, t in enumerate(CHAPTERS):
        out.append((f'CHAPTER_{i}', t))
    for i, t in enumerate(CHNUMS):
        out.append((f'CHNUM_{i}', t))
    for i, t in enumerate(NOTE_TITLES):
        out.append((f'NOTE_TITLE_{i}', t))
    for i, t in enumerate(NOTES):
        out.append((f'NOTE_{i}', t))
    for i, t in enumerate(KEYS):
        out.append((f'KEY_{i}', t))
    for i, t in enumerate(LOCK_HINTS):
        out.append((f'LOCKHINT_{i}', t))
    for i, t in enumerate(DEATHS):
        out.append((f'DEATH_{i}', t))
    return out


COUNTS = dict(NUM_INTRO_PAGES=len(INTRO), NUM_ENDING_PAGES=len(ENDING), NUM_NOTES=len(NOTES),
              NUM_DEATH_MSGS=len(DEATHS))
COUNTS['KEY_MATCHES'] = KEY_MATCHES
BASES = dict(STR_KEY_BASE='KEY_0', STR_LOCKHINT_BASE='LOCKHINT_0')
