from maya import cmds

import avalon.maya


class CreateYetiRig(avalon.maya.Creator):
    """Output for procedural plugin nodes ( Yeti / XGen / etc)"""

    label = "Yeti Rig"
    family = "colorbleed.yetiRig"
    icon = "usb"

    def process(self):

        instance = super(CreateYetiRig, self).process()

        self.log.info("Creating Rig instance set up ...")

        input_meshes = cmds.sets(name="input_SET", empty=True)
        cmds.sets(input_meshes, forceElement=instance)
