# -*- coding: utf-8 -*-
#
# (c) 2016 Boundless, http://boundlessgeo.com
# This code is licensed under the GPL 2.0 license.
#
from lessons.lesson import Step, Lesson
from lessons import utils
from qgis.utils import iface

lesson = Lesson("01. Login to Boundless Connect", "Boundless Connect plugin",
                "lesson.html")

lesson.addStep("New Project", "New Project", iface.newProject)


lesson.addStep("Introduction",
               "01_introduction.md", steptype=Step.MANUALSTEP)
lesson.addStep("Enable Boundless Connect Panel",
               "02_enable_boundless_connect_panel.md", steptype=Step.MANUALSTEP)
lesson.addStep("Enter username and password",
               "03_enter_username_and_password.md", steptype=Step.MANUALSTEP)
lesson.addStep("Set master password", "04_set_master_password.md",
               steptype=Step.MANUALSTEP)
lesson.addStep("Confirm login",
               "05_confirm_login.md", steptype=Step.MANUALSTEP)


lesson.addNextLesson("Boundless Connect plugin", "02. Search Boundless Connect")