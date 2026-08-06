#include "unstructured_mesh.h"
#include <cmath>

namespace tcad {

void UnstructuredMesh::add_node(real_t x, real_t y, real_t z, int region, int contact) {
    nodes_.push_back({x, y, z, region, contact});
}

void UnstructuredMesh::add_triangle(size_t n0, size_t n1, size_t n2) {
    triangles_.push_back({n0, n1, n2});
}

void UnstructuredMesh::add_tetra(size_t n0, size_t n1, size_t n2, size_t n3) {
    tetras_.push_back({n0, n1, n2, n3});
}

void UnstructuredMesh::add_contact_face(const std::vector<size_t>& face_nodes, int contact_id) {
    MeshFace face;
    face.nodes = face_nodes;
    face.contact = contact_id;
    face.area = 0.0Q;  // computed in finalize()
    face.nx = face.ny = face.nz = 0.0Q;
    faces_.push_back(face);
}

void UnstructuredMesh::finalize() {
    // 1. Build unique edges from elements
    std::unordered_map<EdgeKey, size_t, EdgeKeyHash> edge_map;
    edges_.clear();

    auto add_edge = [&](size_t a, size_t b) {
        EdgeKey key(a, b);
        auto it = edge_map.find(key);
        if (it == edge_map.end()) {
            size_t eid = edges_.size();
            MeshEdge edge;
            edge.n0 = a; edge.n1 = b;
            real_t dx = nodes_[a].x - nodes_[b].x;
            real_t dy = nodes_[a].y - nodes_[b].y;
            real_t dz = nodes_[a].z - nodes_[b].z;
            edge.length = sqrt_q(dx*dx + dy*dy + dz*dz);
            if (edge.length > 1e-30Q) {
                edge.nx = dx / edge.length;
                edge.ny = dy / edge.length;
                edge.nz = dz / edge.length;
            }
            edges_.push_back(edge);
            edge_map[key] = eid;
            return eid;
        }
        return it->second;
    };

    // From triangles
    for (const auto& tri : triangles_) {
        add_edge(tri[0], tri[1]);
        add_edge(tri[1], tri[2]);
        add_edge(tri[2], tri[0]);
    }
    // From tetras (6 edges each)
    for (const auto& tet : tetras_) {
        add_edge(tet[0], tet[1]); add_edge(tet[0], tet[2]); add_edge(tet[0], tet[3]);
        add_edge(tet[1], tet[2]); add_edge(tet[1], tet[3]); add_edge(tet[2], tet[3]);
    }

    // 2. Build neighbor list
    neighbor_list_.assign(nodes_.size(), {});
    for (size_t e = 0; e < edges_.size(); ++e) {
        size_t a = edges_[e].n0, b = edges_[e].n1;
        neighbor_list_[a].push_back({b, e});
        neighbor_list_[b].push_back({a, e});
    }

    // 3. Compute face areas and normals
    for (auto& face : faces_) {
        if (face.nodes.size() == 2) {
            // 2D edge face: length
            real_t dx = nodes_[face.nodes[0]].x - nodes_[face.nodes[1]].x;
            real_t dy = nodes_[face.nodes[0]].y - nodes_[face.nodes[1]].y;
            face.area = sqrt_q(dx*dx + dy*dy);
        } else if (face.nodes.size() == 3) {
            // 3D triangle face
            real_t ax = nodes_[face.nodes[1]].x - nodes_[face.nodes[0]].x;
            real_t ay = nodes_[face.nodes[1]].y - nodes_[face.nodes[0]].y;
            real_t az = nodes_[face.nodes[1]].z - nodes_[face.nodes[0]].z;
            real_t bx = nodes_[face.nodes[2]].x - nodes_[face.nodes[0]].x;
            real_t by = nodes_[face.nodes[2]].y - nodes_[face.nodes[0]].y;
            real_t bz = nodes_[face.nodes[2]].z - nodes_[face.nodes[0]].z;
            // Cross product
            real_t cx = ay*bz - az*by;
            real_t cy = az*bx - ax*bz;
            real_t cz = ax*by - ay*bx;
            face.area = 0.5Q * sqrt_q(cx*cx + cy*cy + cz*cz);
            real_t len = sqrt_q(cx*cx + cy*cy + cz*cz);
            if (len > 1e-30Q) {
                face.nx = cx / len; face.ny = cy / len; face.nz = cz / len;
            }
        }
    }

    // 4. Set node contact IDs from contact faces
    for (const auto& face : faces_) {
        if (face.contact >= 0) {
            for (size_t nidx : face.nodes) {
                if (nodes_[nidx].contact < 0)
                    nodes_[nidx].contact = face.contact;
            }
        }
    }
}

} // namespace tcad
