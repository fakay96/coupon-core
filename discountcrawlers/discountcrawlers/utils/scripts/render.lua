-- render.lua
-- Simple Splash Lua script to navigate, wait, and return HTML.

function main(splash, args)
  splash.private_mode_enabled = false
  assert(splash:go(args.url))
  assert(splash:wait(args.wait or 3.0))
  return { html = splash:html() }
end
