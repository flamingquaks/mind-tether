from os import path,environ


    
    
    # def __init__(self) -> None:
    #     pass


_font_dir = path.join("/opt/%s" % (environ['ASSET_LAYER_NAME']),"fonts")
class Font():
    def __init__(self) -> None:
        pass
    
    THE_BOLD_FONT = "%s/theboldfont.ttf" % (_font_dir)
    DEFAULT_FONT = THE_BOLD_FONT
    
class Day():
    __days = {
        "monday": {
            "color": (242,212,214)
        },
        "tuesday": {
            "color": (238,232,184)
        },
        "wednesday": {
            "color": (242,139,132)
        },
        "thursday": {
            "color":(168,206,215)
        },
        "friday":{
            "color": (234,195,138)
        },
        "saturday":{
            "color":(183,181,208)
        },
        "sunday":{
            "color":(166,209,200)
        }
    }
    
    def __init__(self):
        pass
    
    
    @classmethod
    def get_day_color(day: str):
        return Day.__days[day.lower]['color']