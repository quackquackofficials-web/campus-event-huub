# Campus Event Hub — YVIDH Arts Fest Demo

## Demo data
The project includes five YVIDH Arts Fest events for **1 December 2026**:
- Dancing Competition
- Singing Competition
- Fashion Show
- Auto Show
- DJ Night

Venue and event times are intentionally marked as not yet announced. An admin can claim an unassigned event, then update its details, poster, venue, timing and assigned admin.

## Run the project
1. Open this folder in VS Code.
2. Open the integrated Terminal in this folder.
3. Install dependencies: `pip install -r requirements.txt`
4. Start the site: `python app.py`
5. Open `http://127.0.0.1:5000` in your browser.

## Demo workflow
- Create a student account to register for events.
- Create an admin account to manage events.
- In the Admin Panel, use **Take in-charge** on an unassigned demo event.
- Edit the event to add the confirmed venue, time and poster.
- Use the Students and Winners links to manage registrations and results.

## OOPS concepts in `models/event.py`
- **Abstraction:** `Event` is an abstract base class with `event_kind()` as an abstract method.
- **Encapsulation:** event data is stored in the private `__details` attribute and exposed through a safe copy.
- **Inheritance:** `ArtsEvent`, `TechEvent`, `SportsEvent` and `GeneralEvent` inherit from `Event`.
- **Polymorphism:** each subclass overrides `event_kind()`; `event_model_for()` selects the matching class based on the fest.

## Animation integration
`static/js/animation.js` contains the GSAP/AOS integration. `base.html` loads this existing filename. GSAP, ScrollTrigger, ScrollSmoother, SplitText, Draggable, Flip and AOS are loaded by the base template.
