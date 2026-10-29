/** Visitor descriptions, keyed by stable landmark ID rather than translated names. */
export const englishDescriptions: Record<string, string> = {
  'south-gate':
    'A three-bay stone gateway on Daxue East Road, with a taller central bay and the university’s red Chinese name facing south.',
  library:
    'Stepped wings surround reading courtyards. Blue-green glass, pale walls and open white roof frames make the library a campus landmark.',
  huixue:
    'A venue for campus cultural events, with pitched roofs and colonnades that echo the university’s architectural heritage.',
  auditorium:
    'A historic campus building with classical columns and a triangular pediment framing its entrance.',
  stadium:
    'The comprehensive gymnasium on the west campus, defined by a broad shallow-pitched roof, vertical piers and a glazed entrance.',
  'student-center':
    'A student activity space beside Biyun Lake, with flowing floor plates and continuous windows reflected in the water.',
  'teaching-six':
    'A large teaching building on the east campus, with enclosed courtyards and connecting corridors.',
  'teaching-two':
    'Also known as Nanning Building, this west campus teaching building has an elongated form and regular rows of windows.',
  laboratory:
    'A large laboratory building on the southern campus axis, forming the entrance landscape together with the South Gate.',
  computer:
    'A compact, tall teaching and research building on the west campus.',
  'international-residence':
    'A high-rise residence southeast of Biyun Lake, connected to the podium of the former International College building.',
  'new-east-gate':
    'The Xindongyuan entrance on Xiuling Road West Lane 1, with silver fins, a gold university name and an east-side pedestrian entrance beside Student Residence Hall East 25.',
  'east-gate':
    'A stone gateway on Xiuling Road, with a broad central arch, two smaller side arches and a continuous horizontal cornice.',
  'west-gate':
    'The campus entrance on Luban Road, where a tree-lined avenue meets the gatehouse and access facilities.',
  'chongzuo-bridge':
    'An underpass connecting campus areas on either side of Nongyuan Road. Raised walkways meet ramps, with rounded railings along the road.',
  'bocui-bridge':
    'A campus connection along Nongyuan Road, carrying internal traffic beneath the public road.',
  'huixian-bridge':
    'A connection between campus areas on either side of Nongyuan Road, with the public road above and the campus passage below.',
  'time-gate':
    'A silver three-legged sculpture by the Zhou Brothers on the square north of the library. Its three legs symbolize the past, present and future.',
  'teaching-ten':
    'Known as Shijiao, this building north of the square by the east campus library connects a curved low-rise teaching section to a taller northern wing, with smart classrooms and lecture halls.',
  huicui:
    'A campus guest hotel in the north wing of the building shared with the School of Journalism and Communication on the west campus. Its northern entrance has tall columns and a canopy.',
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
