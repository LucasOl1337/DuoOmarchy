-- A complete Omarchy session, with its own home and compositor.
local home = os.getenv("HOME")
dofile((os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/default/hypr/bootstrap.lua")

-- Session services are started locally, never through the host user manager.
package.loaded["default.hypr.autostart"] = true
require("default.hypr.omarchy")
require("hypr.input")
require("hypr.looknfeel")
require("hypr.bindings")
require("default.hypr.toggles")
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

local count = math.max(1, math.min(9, tonumber(os.getenv("DUOOMARCHY_WORKSPACES")) or 9))
for number = 1, count do
  hl.workspace_rule({ workspace = tostring(number), persistent = true, default = number == 1 })
end
hl.unbind("SUPER + code:19")
hl.unbind("SUPER + SHIFT + code:19")
hl.unbind("SUPER + SHIFT + ALT + code:19")

-- Same launcher chords as Lucas, targeting this session's official shell.
for _, chord in ipairs({ "SUPER + SPACE", "SUPER + ALT + SPACE", "SUPER + N" }) do
  hl.unbind(chord)
  o.bind(chord, "Apps menu", "omarchy-menu toggle apps")
end
o.bind("SUPER + A", "Exposé", hl.dsp.event("expose.window-overview:toggle"))
o.bind("SUPER + F12", "Terminal de emergência", "/usr/bin/foot --config=/dev/null /usr/bin/bash --noprofile --norc")

-- Wrappers must take precedence over Omarchy's systemd/UWSM launchers.
hl.env("PATH", home .. "/.local/bin:/usr/share/omarchy/bin:" .. home .. "/.local/share/duoomarchy-host-bin:" .. home .. "/.local/share/mise/shims:/usr/local/bin:/usr/bin:/bin")
hl.on("hyprland.start", function()
  hl.exec_cmd(home .. "/.local/bin/omarchy-launch-shell")
  hl.exec_cmd(home .. "/.local/bin/duoomarchy-session-control --no-autostart --desktop-start")
end)
local custom = home .. "/.config/duoomarchy-work/custom.lua"
local file = io.open(custom, "r")
if file then file:close(); dofile(custom) end
