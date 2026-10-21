# TODO

This project aims to develop STL creations for 3D printing custom pedal mounts for Warwick's Rockboard system. Currently, Warwick has the QuickMount system, but it is only available for certain pedal geometries. We want to extend that to full custom configuration.

The ideal use case would be a user simply inputs the make/model of their pedal, i.e. "Wampler Tumnus Deluxe". We need to then "look-up" the geometry for that pedal - including lower plate screws, etc. for mounting. That could probably be done in multiple query, first by querying the maker website, then on to general web search. A tool (LLM?) or process would need developed to get that info first.

Alternately, the user could provide it in a YAML listing, e.g. Width, Length, Height, Weight, Screws: {Offset_X, Offset_Y, Diameter}.

In either case, we would also be able to have parallel batch options, so that multiple inputs/pedals can be given.

## PREPARATIONS

1. Review the [Warwick Rockboard](https://www.rockboard.de/en/).
2. Gain a clear understanding of the mounting plane and other geometries,
especially for the different Rockboard configurations. Place into documentation.
3. Establish a rendering method to create a STL for the various Rockboard configurations - but don't render a full Rockboard, just that top surface with slots.
4. Review the [Rockboard's QuickMount](https://www.rockboard.de/en/quickmounts/).
5. Gain a clear understanding of the quickmount geometries, especially that funky "keeper" C-pressure lock. For some pedals, we may also need to consider solutions for rubber feet. Keep these in mind with regard to the Rockboard slot spacings. Place result into documentation.
6. Understand how to do "pedal lookup" to get various pedal geometries. Maybe add that in documentation. 

## TASKS

1. Review and create preparation documentation above within "/docs".

2. Develop a staged plan leading to our final goal of user input --> finished STLs for 3D print. Put this in PLAN.md.






