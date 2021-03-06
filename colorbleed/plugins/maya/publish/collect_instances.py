from maya import cmds

import pyblish.api


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by objectSet and pre-defined attribute

    This collector takes into account assets that are associated with
    an objectSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"

    Supported Families:
        avalon.model: Geometric representation of artwork
        avalon.rig: An articulated model for animators.
            A rig may contain a series of sets in which to identify
            its contents.

            - cache_SEL: Should contain cachable polygonal meshes
            - controls_SEL: Should contain animatable controllers for animators
            - resources_SEL: Should contain nodes that reference external files

            Limitations:
                - Only Maya is supported
                - One (1) rig per scene file
                - Unmanaged history, it is up to the TD to ensure
                    history is up to par.
        avalon.animation: Pointcache of `avalon.rig`

    Limitations:
        - Does not take into account nodes connected to those
            within an objectSet. Extractors are assumed to export
            with history preserved, but this limits what they will
            be able to achieve and the amount of data available
            to validators.

    """

    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["maya"]

    def process(self, context):

        objectset = cmds.ls("*.id", long=True, type="objectSet",
                            recursive=True, objectsOnly=True)
        for objset in objectset:

            if not cmds.attributeQuery("id", node=objset, exists=True):
                continue

            id_attr = "{}.id".format(objset)
            if cmds.getAttr(id_attr) != "pyblish.avalon.instance":
                continue

            # The developer is responsible for specifying
            # the family of each instance.
            has_family = cmds.attributeQuery("family",
                                             node=objset,
                                             exists=True)
            assert has_family, "\"%s\" was missing a family" % objset

            members = cmds.sets(objset, query=True)
            if members is None:
                self.log.warning("Skipped empty instance: \"%s\" " % objset)
                continue

            self.log.info("Creating instance for {}".format(objset))

            data = dict()

            # Apply each user defined attribute as data
            for attr in cmds.listAttr(objset, userDefined=True) or list():
                try:
                    value = cmds.getAttr("%s.%s" % (objset, attr))
                except Exception:
                    # Some attributes cannot be read directly,
                    # such as mesh and color attributes. These
                    # are considered non-essential to this
                    # particular publishing pipeline.
                    value = None
                data[attr] = value

            # temporarily translation of `active` to `publish` till issue has
            # been resolved, https://github.com/pyblish/pyblish-base/issues/307
            if "active" in data:
                data["publish"] = data["active"]

            # Collect members
            members = cmds.ls(members, long=True) or []

            # `maya.cmds.listRelatives(noIntermediate=True)` only works when
            # `shapes=True` argument is passed, since we also want to include
            # transforms we filter afterwards.
            children = cmds.listRelatives(members,
                                          allDescendents=True,
                                          fullPath=True) or []
            children = cmds.ls(children, noIntermediate=True, long=True)

            parents = self.get_all_parents(members)
            members_hierarchy = list(set(members + children + parents))

            # Create the instance
            name = cmds.ls(objset, long=False)[0]   # use short name
            instance = context.create_instance(data.get("name", name))
            instance[:] = members_hierarchy
            instance.data["setMembers"] = members
            instance.data.update(data)

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])

        def sort_by_family(instance):
            """Sort by family"""
            return instance.data.get("families", instance.data.get("family"))

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=sort_by_family)

        return context

    def get_all_parents(self, nodes):
        """Get all parents by using string operations (optimization)

        Args:
            nodes (list): the nodes which are found in the objectSet

        Returns:
            list
        """

        parents = []
        for node in nodes:
            splitted = node.split("|")
            items = ["|".join(splitted[0:i]) for i in range(2, len(splitted))]
            parents.extend(items)

        return list(set(parents))
