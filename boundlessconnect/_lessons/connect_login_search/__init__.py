# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from lessons.lesson import Step, Lesson
from lessons import utils
from qgis.utils import iface

lesson = Lesson("Using Boundless Connect", "Boundless Connect plugin",
                "lesson.html")

#lesson.addStep("New Project", "New Project", iface.newProject)


lesson.addStep("Introduction",
               "01_introduction.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Enable Boundless Connect Panel",
               "02_enable_boundless_connect_panel.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Enter username and password",
               "03_enter_username_and_password.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Set master password", "04_set_master_password.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Confirm login",
               "05_confirm_login.md",
               steptype=Step.MANUALSTEP)


lesson.addStep("Search for Knowledge Content",
               "06_searching_for_knowledge_content.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Filter Knowledge results",
               "07_filter_knowledge_results.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Open Knowledge resources",
               "08_open_knowledge_resources.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Search for data",
               "09_search_for_data.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Add data to map",
               "10_add_data_to_map.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Add data to default project",
               "11_add_data_to_default_project.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Search for plugins",
               "12_search_for_plugins.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Install plugins", "13_install_plugins.md",
               steptype=Step.MANUALSTEP)