import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo import _, api, fields, models, tools
import logging
import re
import xml.etree.ElementTree as ET
import random

_logger = logging.getLogger(__name__)


class Venue(models.Model):
    _name = "event.venue"
    _description = ''

    _inherit = ["mail.thread", 'mail.activity.mixin']

    active = fields.Boolean(string="active", default=True, tracking=True)
    name = fields.Char("Name", translate=True, tracking=True)
    location = fields.Text("Address", tracking=True)
    absorptive_capacity = fields.Integer("Absorptive Capacity", compute="_compute_absorptive_capacity")
    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env.company,
        required=False)

    gate_ids = fields.One2many("event.venue.gate", "venue_id", "Gates", tracking=True)
    section_ids = fields.One2many("event.venue.section", "venue_id", "Sections", tracking=True)

    layout_width = fields.Integer("Map width")
    layout_high = fields.Integer("Map high")
    sections_map = fields.Binary(string="Venue Map")
    sections_background = fields.Binary(string="Venue Background")

    @api.onchange('sections_map')
    def _on_sections_map_change(self):
        if self.sections_map:
            svg_data = base64.b64decode(self.sections_map)

            self.extract_viewbox_size(svg_data)

            section_vectors = self._parse_svg_file(svg_data)

            # Clear existing section_ids
            self.section_ids = [(5, 0, 0)]

            # Create new section_ids based on the extracted vectors
            sections = []

            for index, vector in enumerate(section_vectors):
                random_color = '#' + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
                section = {
                    'name': f'Section {chr(65 + (index % 26))}',  # Generate names like 'Section A', 'Section B', etc.
                    'code': f'Sec {index + 1}',  # Generate codes like 'Sec 1', 'Sec 2', etc.
                    'vector_shape': vector,
                    'color': random_color,  # Set appropriate color
                    'absorptive_capacity': 1,  # Set appropriate capacity
                    'closet_gate': False,  # Set appropriate gate
                    'venue_id': self.id,
                }
                sections.append(section)

            self.section_ids = [(0, 0, section_vals) for section_vals in sections]

    def extract_viewbox_size(self, svg_data):
        match = re.search(b'viewBox="([^"]+)"', svg_data)
        if match:
            viewbox = match.group(1).decode('utf-8')
            values = viewbox.split(' ')
            if len(values) == 4:
                width = float(values[2])
                height = float(values[3])
                self.layout_width = int(width)
                self.layout_high = int(height)

    @api.model
    def _parse_svg_file(self, svg_data):
        section_vectors = []

        try:
            root = ET.fromstring(svg_data)
            shape_elements = root.findall(".//{http://www.w3.org/2000/svg}path") + \
                             root.findall(".//{http://www.w3.org/2000/svg}rect") + \
                             root.findall(".//{http://www.w3.org/2000/svg}circle") + \
                             root.findall(".//{http://www.w3.org/2000/svg}ellipse") + \
                             root.findall(".//{http://www.w3.org/2000/svg}polygon") + \
                             root.findall(".//{http://www.w3.org/2000/svg}polyline")

            for shape in shape_elements:
                tag = shape.tag.split("}")[1]  # Extract shape element tag without namespace
                vector = ""

                if tag == "path":
                    vector = shape.get("d")
                elif tag == "rect":
                    x = shape.get("x")
                    y = shape.get("y")
                    width = shape.get("width")
                    height = shape.get("height")
                    vector = f"M{x},{y} h{width} v{height} h-{width} Z"
                elif tag == "circle":
                    cx = shape.get("cx")
                    cy = shape.get("cy")
                    r = shape.get("r")
                    vector = f"M{cx},{cy} m-{r},0 a{r},{r} 0 1,0 {2 * r},0 a{r},{r} 0 1,0 -{2 * r},0"
                elif tag == "ellipse":
                    cx = shape.get("cx")
                    cy = shape.get("cy")
                    rx = shape.get("rx")
                    ry = shape.get("ry")
                    vector = f"M{cx},{cy} m-{rx},0 a{rx},{ry} 0 1,0 {2 * rx},0 a{rx},{ry} 0 1,0 -{2 * rx},0"
                elif tag == "polygon":
                    points = shape.get("points")
                    vector = f"M{points} Z"
                elif tag == "polyline":
                    points = shape.get("points")
                    vector = f"M{points}"

                section_vectors.append(vector)

        except ET.ParseError:
            # Handle parsing error
            pass

        return section_vectors

    def _compute_absorptive_capacity(self):
        for venue in self:
            venue.absorptive_capacity = sum(venue.section_ids.mapped("absorptive_capacity"))


class Gate(models.Model):
    _name = "event.venue.gate"
    _description = ''

    name = fields.Char("Stadium Gate", translate=True)
    code = fields.Char("Code")
    main_gate = fields.Char("Main Gate")
    description = fields.Text("Description")
    gate_keepers = fields.Many2many('res.users', string='Gate Keepers')

    venue_id = fields.Many2one("event.venue")


class Section(models.Model):
    _name = "event.venue.section"
    _description = ''

    name = fields.Char("Name", translate=True)
    code = fields.Char("Code")
    vector_shape = fields.Char("Section Shape",
                               help="Give section a shape as svg vector as 'M5,5 L20,5 L20,50 L5,50 L15,40Z'")
    color = fields.Char(string="Color")
    absorptive_capacity = fields.Integer("Absorptive Capacity")
    closet_gate = fields.Many2one("event.venue.gate")
    venue_id = fields.Many2one("event.venue")
