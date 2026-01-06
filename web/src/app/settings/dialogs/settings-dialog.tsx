// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { Settings, LogOut } from "lucide-react";
import { useTranslations } from 'next-intl';
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Tooltip } from "~/components/deer-flow/tooltip";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import { Tabs, TabsContent } from "~/components/ui/tabs";
import { useReplay } from "~/core/replay";
import {
  type SettingsState,
  changeSettings,
  saveSettings,
  useSettingsStore,
} from "~/core/store";
import { cn } from "~/lib/utils";
import { useAuth } from "~/core/contexts/auth-context";

import { SETTINGS_TABS } from "../tabs";

export function SettingsDialog() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const { isReplay } = useReplay();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [activeTabId, setActiveTabId] = useState(SETTINGS_TABS[0]!.id);
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState(useSettingsStore.getState());
  const [changes, setChanges] = useState<Partial<SettingsState>>({});

  const handleLogout = useCallback(() => {
    logout();
    setOpen(false);
    router.push('/login');
  }, [logout, router]);

  const handleTabChange = useCallback(
    (newChanges: Partial<SettingsState>) => {
      setTimeout(() => {
        if (open) {
          setChanges((prev) => ({
            ...prev,
            ...newChanges,
          }));
        }
      }, 0);
    },
    [open],
  );

  const handleSave = useCallback(() => {
    if (Object.keys(changes).length > 0) {
      const newSettings: SettingsState = {
        ...settings,
        ...changes,
      };
      setSettings(newSettings);
      setChanges({});
      changeSettings(newSettings);
      saveSettings();
    }
    setOpen(false);
  }, [settings, changes]);

  const handleOpen = useCallback(() => {
    setSettings(useSettingsStore.getState());
  }, []);

  const handleClose = useCallback(() => {
    setChanges({});
  }, []);

  useEffect(() => {
    if (open) {
      handleOpen();
    } else {
      handleClose();
    }
  }, [open, handleOpen, handleClose]);

  const mergedSettings = useMemo<SettingsState>(() => {
    return {
      ...settings,
      ...changes,
    };
  }, [settings, changes]);

  if (isReplay) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Tooltip title={tCommon('settings')}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon">
            <Settings />
          </Button>
        </DialogTrigger>
      </Tooltip>
      <DialogContent className="sm:max-w-[850px]">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
          <DialogDescription>
            {t('description')}
          </DialogDescription>
        </DialogHeader>
        <Tabs value={activeTabId}>
          <div className="flex h-120 w-full overflow-auto border-y">
            <ul className="flex w-50 shrink-0 border-r p-1">
              <div className="size-full">
                {SETTINGS_TABS.map((tab) => (
                  <li
                    key={tab.id}
                    className={cn(
                      "hover:accent-foreground hover:bg-accent mb-1 flex h-8 w-full cursor-pointer items-center gap-1.5 rounded px-2",
                      activeTabId === tab.id &&
                      "!bg-primary !text-primary-foreground",
                    )}
                    onClick={() => setActiveTabId(tab.id)}
                  >
                    <tab.icon size={16} />
                    <span>{tab.label}</span>
                    {tab.badge && (
                      <Badge
                        variant="outline"
                        className={cn(
                          "border-muted-foreground text-muted-foreground ml-auto px-1 py-0 text-xs",
                          activeTabId === tab.id &&
                          "border-primary-foreground text-primary-foreground",
                        )}
                      >
                        {tab.badge}
                      </Badge>
                    )}
                  </li>
                ))}
              </div>
            </ul>
            <div className="min-w-0 flex-grow">
              <div
                id="settings-content-scrollable"
                className="size-full overflow-auto p-4"
              >
                {SETTINGS_TABS.map((tab) => (
                  <TabsContent key={tab.id} value={tab.id}>
                    <tab.component
                      settings={mergedSettings}
                      onChange={handleTabChange}
                    />
                  </TabsContent>
                ))}
              </div>
            </div>
          </div>
        </Tabs>
        <DialogFooter className="flex justify-between sm:justify-between">
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-sm text-muted-foreground">
                Signed in as <span className="font-medium">{user.name}</span>
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button className="w-24" type="submit" onClick={handleSave}>
              {tCommon('save')}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
