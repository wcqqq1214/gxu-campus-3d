/** Visitor descriptions, keyed by stable landmark ID rather than translated names. */
export const englishDescriptions: Record<string, string> = {
  'south-gate':
    'A three-bay stone gateway on Daxue East Road, with a taller central bay and the university’s red Chinese name facing south.',
  'south-side-gate':
    'A functional entrance beside the Xueyuan Building on Daxue East Road, with divided vehicle lanes, a central checkpoint and pedestrian passages toward the light industry precinct.',
  library:
    'Stepped wings frame quiet reading courtyards, clad in blue-green glass and pale walls with open white roof frames.',
  huixue:
    'A campus hall for performances and cultural events, with dark pitched roofs and colonnades in the university’s traditional style.',
  auditorium:
    'A historic campus building with classical columns and a triangular pediment framing its entrance.',
  stadium:
    'The comprehensive gymnasium on the west campus, defined by a broad shallow-pitched roof, vertical piers and a glazed entrance.',
  'student-center':
    'A student activity space beside Biyun Lake, with flowing floor plates and continuous windows reflected in the water. A spiral stair leads to the Old Water Tower Café at the west end of the second floor. Window seats look onto the brick tower.',
  'teaching-six':
    'A large teaching complex on the east campus, built around three enclosed courtyards linked by corridors with entrances on all four sides.',
  'teaching-two':
    'Also known as Nanning Building, this long teaching block on the west campus features regular rows of windows.',
  laboratory:
    'A large laboratory building along the southern campus axis behind the South Gate, with a stepped front facade.',
  computer:
    'A compact high-rise teaching and research building on the west campus, with a vertical glass core and pink side walls.',
  'international-residence':
    'A high-rise residence southeast of Biyun Lake, connected to the podium of the former International College building.',
  'new-east-gate':
    'The Xindongyuan entrance on Xiuling Road West Lane 1, with silver fins, a gold university name and an east-side pedestrian entrance beside Student Residence Hall East 25.',
  'east-gate':
    'A stone gateway on Xiuling Road, with a broad central arch, two smaller side arches and a continuous horizontal cornice.',
  'west-gate':
    'A curved beige gatehouse and a university name wall with a sloping edge mark the tree-lined entrance on Luban Road.',
  'chongzuo-bridge':
    'An underpass connecting campus areas on either side of Nongyuan Road. Raised walkways meet ramps, with rounded railings along the road.',
  'bocui-bridge':
    'A campus connection along Nongyuan Road, carrying internal traffic beneath the public road.',
  'huixian-bridge':
    'An underpass connecting campus areas across Nongyuan Road, with the public street above and campus paths below.',
  'time-gate':
    'A silver three-legged sculpture by the Zhou Brothers on the square north of the library. Its three legs symbolize the past, present and future.',
  'teaching-ten':
    'Known as Shijiao, this building north of the square by the east campus library connects a curved low-rise teaching section to a taller northern wing, with smart classrooms and lecture halls.',
  huicui:
    'A campus guest hotel occupying the north wing of the building shared with the School of Journalism and Communication on the west campus, fronted by tall columns and a canopy. Huicui Dining Hall is on the seventh floor via the north lobby elevators.',
};

export function landmarkDescription(
  place: { id: string; description: string },
  locale: 'zh' | 'en',
) {
  if (locale === 'en')
    return englishDescriptions[place.id] ?? place.description;
  // Preserve source data while making the historical institution status clear to visitors.
  return place.id === 'international-residence'
    ? place.description.replace('国际学院裙楼', '原国际学院裙楼')
    : place.description;
}
