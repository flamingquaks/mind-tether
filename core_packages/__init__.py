

class Device:
    """This is how device details are stored and passed around.
    """    
    def __init__(self,*args,screen_height:int,screen_width:int) -> None:
        """
        Args:
            screen_height (int): The height (in pixels) of the screen
            screen_width (int): The width (in pixels) of the screen
        """        
        self._screen_height = screen_height
        self._screen_width = screen_width
        
    @property
    def screen_height(self):
        return self._screen_height
    
    @screen_height.setter
    def screen_height(self, screen_height):
        self._screen_height=screen_height
         
    @property
    def screen_width(self):
        return self._screen_width
    
    @screen_width.setter
    def screen_width(self,screen_width):
        self._screen_width = screen_width
