I got sick of performance concerns and having rulesets be significant one-off projects. I thought, if I could do sufficient learning on just the HTML of a page, I could (1) do it all offthread and (2) not have to worry about those expensive DOM routines. So I tried an experiment. I wrote a shopping-page classifier, like the one we have. I didn't even feed it all the samples: less than half, in fact. And it matched the accuracy of old Shopping ruleset, that took us a month to write, on the first try.

And actually, I wrote a general classifier: I didn't program anything shopping-specific, not so much as a price regex. This is a general binary classifier that should work on any natural language that puts spaces between its words.

So I am very excited at the prospect of being able to target arbitrary categories just by collecting a few hundred samples each, with no additional programming.

I haven't even really taught the thing about HTML yet, so there should be a lot of low-hanging fruit remaining.