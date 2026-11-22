// Rebuild Draco vertex connectivity using independent position/normal/UV maps.
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <vector>
#include "draco/attributes/attribute_quantization_transform.h"
#include "draco/attributes/attribute_octahedron_transform.h"
#include "draco/compression/decode.h"
#include "draco/compression/expert_encode.h"

namespace d = draco;
using G = d::GeometryAttribute;

std::unique_ptr<d::Mesh> read_mesh(const std::string &data, bool integers) {
    d::Decoder decoder;
    if (integers) {
        decoder.SetSkipAttributeTransform(G::POSITION);
        decoder.SetSkipAttributeTransform(G::NORMAL);
        decoder.SetSkipAttributeTransform(G::TEX_COORD);
    }
    d::DecoderBuffer buffer;
    buffer.Init(data.data(), data.size());
    auto result = decoder.DecodeMeshFromBuffer(&buffer);
    if (!result.ok()) throw std::runtime_error(result.status().error_msg_string());
    return std::move(result).value();
}

void compress(const char *input, const char *output) {
    std::ifstream file(input, std::ios::binary);
    std::string bytes((std::istreambuf_iterator<char>(file)), {});
    auto mesh = read_mesh(bytes, false);
    auto portable = read_mesh(bytes, true);
    if (!mesh->DeduplicateAttributeValues()) throw std::runtime_error("attribute sharing failed");
    auto *position = mesh->attribute(mesh->GetNamedAttributeId(G::POSITION));
    std::vector<bool> protect(mesh->num_points());
    for (d::FaceIndex f(0); f < mesh->num_faces(); ++f) {
        auto face = mesh->face(f);
        for (int i = 0; i < 3; ++i) {
            auto a = face[i], b = face[(i + 1) % 3];
            if (position->mapped_index(a) == position->mapped_index(b)) {
                protect[a.value()] = protect[b.value()] = true;
            }
        }
    }
    // Edgebreaker would discard a face with two equal position indices.
    // Preserve such point identities even though their positions match.
    size_t next = position->size();
    position->Resize(next + std::count(protect.begin(), protect.end(), true));
    for (d::PointIndex i(0); i < mesh->num_points(); ++i) {
        if (!protect[i.value()]) continue;
        std::array<float, 3> value;
        position->GetMappedValue(i, value.data());
        d::AttributeValueIndex ix(next++);
        position->SetAttributeValue(ix, value.data());
        position->SetPointMapEntry(i, ix);
    }
    mesh->DeduplicatePointIds();
    d::ExpertEncoder encoder(*mesh);
    encoder.SetSpeedOptions(0, 0);
    for (auto semantic : {G::POSITION, G::TEX_COORD}) {
        int id = mesh->GetNamedAttributeId(semantic);
        auto *a = portable->GetNamedAttribute(semantic);
        d::AttributeQuantizationTransform q;
        if (!q.InitFromAttribute(*a)) throw std::runtime_error("missing source grid");
        encoder.SetAttributeExplicitQuantization(id, q.quantization_bits(), a->num_components(),
                                                 q.min_values().data(), q.range());
        std::cerr << id << " quantization " << q.quantization_bits() << " range " << q.range() << "\n";
    }
    d::AttributeOctahedronTransform normal;
    if (!normal.InitFromAttribute(*portable->GetNamedAttribute(G::NORMAL))) {
        throw std::runtime_error("missing original octahedral normal transform");
    }
    encoder.SetAttributeQuantization(mesh->GetNamedAttributeId(G::NORMAL), normal.quantization_bits());
    d::EncoderBuffer result;
    auto status = encoder.EncodeToBuffer(&result);
    if (!status.ok()) throw std::runtime_error(status.error_msg_string());
    std::ofstream out(output, std::ios::binary);
    out.write(result.data(), result.size());
    if (!out) throw std::runtime_error("cannot write encoded terrain");
    std::cerr << "payload " << result.size() << " bytes\n";
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    try { compress(argv[1], argv[2]); }
    catch (const std::exception &e) { std::cerr << e.what() << "\n"; return 1; }
}
