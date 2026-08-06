#pragma once

#include "mesh.h"
#include <unordered_map>
#include <set>

namespace tcad {

// Unstructured triangular (2D) / tetrahedral (3D) mesh
class UnstructuredMesh : public Mesh {
public:
    // Build from node positions + triangle/tetra connectivity
    // 2D: triangles = (n0, n1, n2) per element
    // 3D: tetras = (n0, n1, n2, n3) per element

    void add_node(real_t x, real_t y, real_t z, int region = 0, int contact = -1);
    void add_triangle(size_t n0, size_t n1, size_t n2);
    void add_tetra(size_t n0, size_t n1, size_t n2, size_t n3);
    void add_contact_face(const std::vector<size_t>& face_nodes, int contact_id);

    // Finalize: build edges, neighbors, faces
    void finalize();

    // Set material properties
    void set_permittivity(const std::vector<real_t>& eps) { eps_ = eps; }

    // --- Mesh interface ---
    size_t npts() const override { return nodes_.size(); }
    size_t nedges() const override { return edges_.size(); }
    size_t nfaces() const override { return faces_.size(); }

    real_t node_x(size_t i) const override { return nodes_[i].x; }
    real_t node_y(size_t i) const override { return nodes_[i].y; }
    real_t node_z(size_t i) const override { return nodes_[i].z; }
    int node_region(size_t i) const override { return nodes_[i].region; }
    int node_contact(size_t i) const { return nodes_[i].contact; }

    size_t edge_n0(size_t e) const override { return edges_[e].n0; }
    size_t edge_n1(size_t e) const override { return edges_[e].n1; }
    real_t edge_length(size_t e) const override { return edges_[e].length; }

    int face_contact(size_t f) const override { return faces_[f].contact; }
    real_t face_area(size_t f) const override { return faces_[f].area; }

    const std::vector<std::pair<size_t, size_t>>& neighbors(size_t i) const override {
        return neighbor_list_[i];
    }

    real_t eps(size_t i) const override {
        return (i < eps_.size()) ? eps_[i] : 11.7Q * 8.854187817e-12Q;
    }

    // Direct access for solvers
    const std::vector<MeshNode>& nodes() const { return nodes_; }
    const std::vector<MeshEdge>& edges() const { return edges_; }
    const std::vector<MeshFace>& faces() const { return faces_; }

    // Get all nodes on a specific contact
    std::vector<size_t> contact_nodes(int contact_id) const {
        std::vector<size_t> result;
        for (size_t i = 0; i < nodes_.size(); ++i)
            if (nodes_[i].contact == contact_id)
                result.push_back(i);
        return result;
    }

private:
    std::vector<MeshNode> nodes_;
    std::vector<MeshEdge> edges_;
    std::vector<MeshFace> faces_;
    std::vector<std::vector<std::pair<size_t, size_t>>> neighbor_list_;
    std::vector<real_t> eps_;

    // Elements (triangles or tetras)
    std::vector<std::array<size_t, 3>> triangles_;
    std::vector<std::array<size_t, 4>> tetras_;

    // Edge deduplication
    struct EdgeKey {
        size_t a, b;
        EdgeKey(size_t n0, size_t n1) : a(std::min(n0, n1)), b(std::max(n0, n1)) {}
        bool operator==(const EdgeKey& o) const { return a == o.a && b == o.b; }
    };
    struct EdgeKeyHash {
        size_t operator()(const EdgeKey& k) const {
            return k.a * 1000003 + k.b;
        }
    };
};

} // namespace tcad
