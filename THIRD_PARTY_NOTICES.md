# Third-party notices

## Swiss Ephemeris

GetBirthChart Core uses Swiss Ephemeris through the `pyswisseph` Python
package for planetary, lunar, node, house, and angle calculations. Swiss
Ephemeris is copyright Astrodienst AG, Switzerland, and is made available by
its authors under a dual-licensing system:

- GNU Affero General Public License (AGPL)
- Swiss Ephemeris Professional License

This project uses the GNU AGPL path for the engine. That statement does not
change the separate upstream terms for Swiss Ephemeris itself or for any
ephemeris data files. The repository does not commit or redistribute `.se1`
files; production operators must provision them under the applicable upstream
terms.

Official licensing information:
<https://www.astro.com/swisseph/swephinfo_e.htm>

The Python binding used by the optional `swiss` extra is `pyswisseph`:
<https://pypi.org/project/pyswisseph/>
