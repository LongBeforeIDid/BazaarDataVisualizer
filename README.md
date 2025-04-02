# Bazaar Data Visualizer

## Description

A simple GUI tool that allows you to visualize and compare the expected output of two items for a given combat duration and percentage of cooldown reduction applied.

Currently, it only functions for basic damage, heal, and shield items (while the app uses the terms "weapon" and "damage" exclusively, the numbers would be identical for heal and shield items as well.) I entend to add more features, including poison and fire calculations, accounting for item size, and to allow the user to map other variables to the y axis instead of cooldown reduction (e.g expected haste uptime, crit chance, etc.).

## User Guide

How should you use this tool? That's entirely up to you. It's faily limited in its current state, and The Bazaar is a very complex game with lots of edge cases and complicating factors. It never hurts to have more information though, and messing around with seeing how different values generate different heatmaps might help develop your intuition for how a given item will perform.

Right now, I think it's best suited to helping make decisions on Day 1 and Day 2 

## Documentation

### Tab One and Two

The first two tabs allow you to generate a heatmap of expected damage output for a particular item. When you hover over a square on the heatmap, it will tell you the expected output for that specific intersection of combat duration and CDR.

Damage: Self explanatory. The base value on the item. Could be heal or shield as well.
Mult: Multiplier to base damage (either from multicast or obsidian)
Base Cooldown: Item's cooldown without applying CDR.

Low Cap: This pegs the low end of the colormap to whatever value is entered. Leave blank for automatic fit.
High Cap: This pegs the high end of the colormap to whatever value is entered. Leave blank for automatic fit.

[!TIP]
These settings are only visual, they don't change any values or the actual range of the heatmap. You most likely want to leave them blank. There are two main reasons you would want to adjust these values: 
1. You want to normalize the colormap so you can visually compare the charts of two items more easily, in which case you should make sure these values are equal for both items
2. Your weapon scales exponentially and you've lost detail in important parts of your heatmap (i.e if the very upper right corner is green but the rest of the heatmap is uniform red, you may want to set High Cap to a more sensible number.) 

Maximum CDR: This scales the range of values on the y-axis, with 10 being the minimum. Setting it to 100 will give you a prettier chart, but you should probably set it much lower, within the range of CDR you expect is possible for your situation.

End at storm: By default, the x-axis has a range of 60 seconds. If this box is checked, it will truncate the range of the x-axis to 30 seconds.

[!WARNING]
"Maximum CDR" and "End at storm" affect the actual dimensions of the generated heatmap. If you want to generate a comparison heatmap for two items, you must ensure that these values are consistent across both of them such that their dimensions are the same.

### Comparison Tab

Absolute Damage: When checked, 



To install them, run:
```bash
pip install -r requirements.txt
```
