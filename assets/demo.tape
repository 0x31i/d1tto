# d1tto demo. Regenerate with:  vhs assets/demo.tape   (needs d1tto installed)
Output assets/demo.gif

Set Shell "bash"
Set FontSize 20
Set Width 1200
Set Height 780
Set Padding 22
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set TypingSpeed 55ms

# --- hidden setup: isolated config, throwaway vault, clipboard payload ---
Hide
Type "source assets/demo_setup.sh" Enter
Sleep 500ms
Show

# --- the demo ---
Type "d1tto" Enter
Sleep 1.6s
Type "Acme Corp" Enter
Sleep 900ms
Type "10.0.0.0/24, portal.acme.com" Enter
Sleep 1.8s
Type "box .5 runs jenkins 2.426 with no auth" Enter
Sleep 1.4s
Type "bash c" Enter
Sleep 1.4s
Type ":finding high SQLi in the portal login" Enter
Sleep 1.4s
Type ":ls" Enter
Sleep 2s
Type ":q" Enter
Sleep 2.2s
