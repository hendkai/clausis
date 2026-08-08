/* Clausis Shell Bridge
 *
 * GNOME Shell is not part of the AT-SPI tree, and Wayland offers no supported
 * way to reach the overview from another process.  This extension exports a
 * deliberately tiny session-bus interface: every method is parameterless and
 * maps to one fixed shell surface.  There is no eval, no coordinate handling,
 * no input simulation and no way to name an arbitrary shell object, so a
 * compromised Clausis session process gains nothing beyond these surfaces.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BUS_NAME = 'org.clausis.Shell1';
const OBJECT_PATH = '/org/clausis/Shell1';

const INTERFACE = `
<node>
  <interface name="org.clausis.Shell1">
    <method name="ShowOverview">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="HideOverview">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="ShowApplications">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="ShowQuickSettings">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="ShowNotifications">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="MinimizeWindow">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="MaximizeWindow">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="UnmaximizeWindow">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="NextWorkspace">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="PreviousWorkspace">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="MoveWindowToNextWorkspace">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="MoveWindowToPreviousWorkspace">
      <arg type="s" direction="out" name="result"/>
    </method>
    <method name="ReadClipboard">
      <arg type="s" direction="out" name="result"/>
    </method>
  </interface>
</node>`;

class ClausisShellService {
    constructor() {
        this._exported = Gio.DBusExportedObject.wrapJSObject(INTERFACE, this);
        this._nameId = 0;
    }

    export() {
        this._exported.export(Gio.DBus.session, OBJECT_PATH);
        this._nameId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            null,
            null,
            null);
    }

    unexport() {
        if (this._nameId !== 0) {
            Gio.bus_unown_name(this._nameId);
            this._nameId = 0;
        }
        this._exported.unexport();
    }

    ShowOverview() {
        Main.overview.show();
        return 'overview';
    }

    HideOverview() {
        Main.overview.hide();
        return 'desktop';
    }

    ShowApplications() {
        Main.overview.show();
        if (Main.overview.dash?.showAppsButton)
            Main.overview.dash.showAppsButton.checked = true;
        return 'applications';
    }

    ShowQuickSettings() {
        this._toggleMenu('quickSettings');
        return 'quick-settings';
    }

    ShowNotifications() {
        this._toggleMenu('dateMenu');
        return 'notifications';
    }

    MinimizeWindow() {
        this._focusedWindow().minimize();
        return 'minimized';
    }

    MaximizeWindow() {
        this._focusedWindow().maximize(Meta.MaximizeFlags.BOTH);
        return 'maximized';
    }

    UnmaximizeWindow() {
        this._focusedWindow().unmaximize(Meta.MaximizeFlags.BOTH);
        return 'unmaximized';
    }

    NextWorkspace() {
        return this._switchWorkspace(1, false);
    }

    PreviousWorkspace() {
        return this._switchWorkspace(-1, false);
    }

    MoveWindowToNextWorkspace() {
        return this._switchWorkspace(1, true);
    }

    MoveWindowToPreviousWorkspace() {
        return this._switchWorkspace(-1, true);
    }

    // Reading is the only clipboard direction exposed here. Writing would need
    // an input argument, which this interface deliberately does not have; the
    // AT-SPI copy action on the focused widget covers that direction instead.
    // St.Clipboard.get_text is callback based, so this method uses the GJS
    // async convention and returns once the clipboard has actually answered.
    ReadClipboardAsync(params, invocation) {
        St.Clipboard.get_default().get_text(
            St.ClipboardType.CLIPBOARD,
            (_clipboard, value) => {
                const text = (value ?? '').slice(0, 2000);
                invocation.return_value(new GLib.Variant('(s)', [text]));
            });
    }

    _toggleMenu(name) {
        const indicator = Main.panel.statusArea[name];
        if (!indicator?.menu)
            throw new Error(`shell surface ${name} is unavailable`);
        indicator.menu.toggle();
    }

    _focusedWindow() {
        const window = global.display.focus_window;
        if (!window)
            throw new Error('no focused window');
        return window;
    }

    _switchWorkspace(offset, withWindow) {
        const manager = global.workspace_manager;
        const index = manager.get_active_workspace_index() + offset;
        if (index < 0 || index >= manager.get_n_workspaces())
            throw new Error('no such workspace');
        const workspace = manager.get_workspace_by_index(index);
        if (withWindow)
            this._focusedWindow().change_workspace_by_index(index, false);
        workspace.activate(global.get_current_time());
        return `workspace-${index}`;
    }
}

export default class ClausisExtension extends Extension {
    enable() {
        this._service = new ClausisShellService();
        this._service.export();
    }

    disable() {
        this._service?.unexport();
        this._service = null;
    }
}
