class MusicEvent(object):

  def __init__(self, xml_note, state):
    self.xml_note = xml_note
    self.tie_stop = False
    self.tie_start = False
    self._parse()

  def _parse(self):

    for child in self.xml_note:
      if child.tag == 'tie':
        if child.attrib['type'] == 'start':
          self.tie_start = True
        elif child.attrib['type'] == 'stop':
          self.tie_stop = True
