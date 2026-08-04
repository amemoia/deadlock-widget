# Discord deprecated custom widgets, this will no longer work!

A custom Deadlock widget updater for Discord. Requires an already set up Discord Application with a Profile Widget.

Requires installing [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html#windows)

I recommend Chloe Cinders [Custom Widget Guide](https://chloecinders.com/blog/discord-widgets) if you're looking to set one up. Please see the [Widget Config](#widget-config) section of this README to set the widget up to work with this.

This script searches for the Steam install directory in Program Files (x86), but you can change the directory by modifying `SCR_DIR` in `modules/consts.py`. I have not tested this on Linux at all though. A manual mode also exists in case the script can't read your stats well

## Usage

Here's what the script does:

1. Take a screenshot of your Deadlock stats page using Steam (F12 by default)
2. Run the script
3. Script looks for the latest screenshot taken with Steam
4. Runs OCR to get the following data: nickname, most played hero, games played, games won, commends, kills, assists, denies
5. Sends the resulting data to Discord to update your widget

To use this script, download and extract the repository somewhere and run `python main.py` or just use one of the `.bat` files (you will need Python 3.10 or higher)

Required Python modules should automatically install from `requirements.txt` if missing

## Variables

Missing mandatory environment variables can be entered into the console when the script is run

Alternatively, create a `.env` file with the following:
- `DISCORD_APPLICATION_ID` - the application ID your widget belongs to
- `DISCORD_USER_ID` - the user we're updating the widget for
- `DISCORD_WIDGET_USERNAME` - doesnt rly matter can be whatever
- `DISCORD_BOT_TOKEN` - the bot token tied to the same application, DO NOT SHARE THIS WITH ANYONE !!!!!!!!!!!!!!!

Optional:
- `DISCORD_IDENTITY_ID` - defaults to `0` which the widget guide recommends using, if you know what you're doing feel free to change this
- `DISCORD_WIDGET_HERO_IMAGE_BASE_URL` - a place where all the hero renders taken from the deadlock wiki are stored, defaults to this repository's renders on github
- `DISCORD_WIDGET_DEBUG_REGIONS=1` - debug stuff, outputs an image with ocr region boxes drawn and also outputs each crop in the /debug folder

Note regarding hero renders: if you're planning to host them somewhere yourself, the script expects the same filenames that the Deadlock wiki uses. In the same folder, hero cards should be present. They follow the same naming convention except they have `_card` instead of `_Render` at the end

For testing purposes:
- `DISCORD_WIDGET_MANUAL_MODE=1` will entirely skip the OCR step and allow you to enter values manually

## Widget config
Follow the Chloe Cinders guide linked above to set up a widget yourself.

Here's the expected widget configuration, it may look compicated but it shouldn't take too long to set up

1. Widget Top
    - Design: Hero
    - Image:
        - Value Type: `User Data`
        - Data Field: `hero_image_url`
    - Title:
        - Presentation Type: `Text`
        - Value Type: `User Data`
        - Data Field: `nickname`
    - Subtitle 1:
        - Value Type: `User Data`
        - Data Field: `top_hero`
        - Enable Label
            - Presentation Type: `Text`
            - Value Type: `Custom String`
            - Content: `Most played`

2. Widget Bottom
    - Design: Stats Grid
    - Stat #1
        - Presentation Type: `Number`
        - Value Type: `User Data`
        - Data Field: `games_played`
        - Enable Label
            - Value Type: `Custom String`
            - Content: `Games played`
    - Stat #2
        - Presentation Type: `Number`
        - Value Type: `User Data`
        - Data Field: `games_won`
        - Enable Label
            - Value Type: `Custom String`
            - Content: `Wins`
    - Stat #3
        - Presentation Type: `Number`
        - Value Type: `User Data`
        - Data Field: `commends`
        - Enable Label
            - Presentation Type: `Text`
            - Value Type: `Custom String`
            - Content: `Commends`
    - Stat #4
        - Presentation Type: `Number`
        - Value Type: `User Data`
        - Data Field: `kills`
        - Enable Label
            - Presentation Type: `Text`
            - Value Type: `Custom String`
            - Content: `Kills`
    - Stat #5
        - Presentation Type: `Number`
        - Value Type: `User Data`
        - Data Field: `assists`
        - Enable Label
            - Presentation Type: `Text`
            - Value Type: `Custom String`
            - Content: `Assists`
    - Stat #6
        - Presentation Type: `Number`
        - Value Type: `User Data`
        - Data Field: `denies`
        - Enable Label
            - Presentation Type: `Text`
            - Value Type: `Custom String`
            - Content: `Soul denies`

3. Add Widget Preview
    - Design: Hero
    - Hero Image
        - Value Type: `Application Asset`
        - Asset Key: Click the little gallery icon next to the field, click Add Asset, upload one of the hero cards and select it

4. (Optional) Mini Profile
    - Design: Hero Stat
    - Stat:
        - Value Type: `User Data`
        - Data Field: `top_hero`
        - Enable Label
            - Presentation Type: `Text`
            - Value Type: `Custom String`
            - Content: `Most played`
    - Hero Image:
        - Value Type: `User Data`
        - Data Field: `hero_card_url`
