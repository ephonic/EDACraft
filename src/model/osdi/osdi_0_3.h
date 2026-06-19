// osdi_0_3.h — OSDI (Open Source Device Interface) v0.3 C 绑定
//
// 本头文件是 SemiMod OSDI 规范 v0.3 的 C 接口定义，逐字节对齐 OpenVAF 输出的 ABI。
// 来源：OpenVAF 仓库 openvaf/osdi/header/osdi_0_3.h（权威定义）。
// 仿真器通过此接口加载并调用 OpenVAF 编译的 Verilog-A 器件模型。
//
// 加载流程（参见 OpenVAF openvaf/osdi/src/lib.rs 第180行 export_array）：
//   1. dlopen/LoadLibrary 加载模型共享库
//   2. dlsym("OSDI_DESCRIPTORS")     -> OsdiDescriptor*  (每个模型一个)
//   3. dlsym("OSDI_NUM_DESCRIPTORS") -> uint32_t
//   4. dlsym("OSDI_VERSION_MAJOR/MINOR") -> 校验版本(0,3)
//   5. 按 descriptor->name 匹配网表中的 .model 名
//   6. malloc(descriptor->model_size) + setup_model 初始化模型数据块
//   7. malloc(descriptor->instance_size) + setup_instance 初始化实例数据块
//   8. 求解时: eval() 计算 + load_residual_resist/load_jacobian_resist 取回贡献
#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define OSDI_VERSION_MAJOR_CURR 0
#define OSDI_VERSION_MINOR_CURR 3

/* 参数类型与类别位掩码 */
#define PARA_TY_MASK 3
#define PARA_TY_REAL 0
#define PARA_TY_INT  1
#define PARA_TY_STR  2
#define PARA_KIND_MASK  (3 << 30)
#define PARA_KIND_MODEL (0 << 30)
#define PARA_KIND_INST  (1 << 30)
#define PARA_KIND_OPVAR (2 << 30)

#define ACCESS_FLAG_READ     0
#define ACCESS_FLAG_SET      1
#define ACCESS_FLAG_INSTANCE 4

/* Jacobian entry flags: 区分电阻性(同相)/电抗性(正交)贡献 */
#define JACOBIAN_ENTRY_RESIST_CONST 1
#define JACOBIAN_ENTRY_REACT_CONST  2
#define JACOBIAN_ENTRY_RESIST       4
#define JACOBIAN_ENTRY_REACT        8

/* eval 调用的计算标志位（控制 eval 计算哪些量并存储到实例数据块）*/
#define CALC_RESIST_RESIDUAL  1
#define CALC_REACT_RESIDUAL   2
#define CALC_RESIST_JACOBIAN  4
#define CALC_REACT_JACOBIAN   8
#define CALC_NOISE           16
#define CALC_OP              32
#define CALC_RESIST_LIM_RHS  64
#define CALC_REACT_LIM_RHS  128
#define ENABLE_LIM          256
#define INIT_LIM            512
#define ANALYSIS_NOISE     1024
#define ANALYSIS_DC        2048
#define ANALYSIS_AC        4096
#define ANALYSIS_TRAN      8192
#define ANALYSIS_IC       16384
#define ANALYSIS_STATIC   32768
#define ANALYSIS_NODESET  65536

/* eval 返回标志 */
#define EVAL_RET_FLAG_LIM    1
#define EVAL_RET_FLAG_FATAL  2
#define EVAL_RET_FLAG_FINISH 4
#define EVAL_RET_FLAG_STOP   8

/* 日志级别 */
#define LOG_LVL_MASK 7
#define LOG_LVL_DEBUG   0
#define LOG_LVL_DISPLAY 1
#define LOG_LVL_INFO    2
#define LOG_LVL_WARN    3
#define LOG_LVL_ERR     4
#define LOG_LVL_FATAL   5
#define LOG_FMT_ERR    16

#define INIT_ERR_OUT_OF_BOUNDS 1

typedef struct OsdiLimFunction {
  char *name;
  uint32_t num_args;
  void *func_ptr;
} OsdiLimFunction;

typedef struct OsdiSimParas {
  char **names;
  double *vals;
  char **names_str;
  char **vals_str;
} OsdiSimParas;

typedef struct OsdiSimInfo {
    OsdiSimParas paras;
    double abstime;
    double *prev_solve;   /* 上一步节点电压解（节点电压 + 分支电流） */
    double *prev_state;
    double *next_state;
    uint32_t flags;       /* CALC_* 与 ANALYSIS_* 标志 */
} OsdiSimInfo;

typedef union OsdiInitErrorPayload {
  uint32_t parameter_id;
} OsdiInitErrorPayload;

typedef struct OsdiInitError {
  uint32_t code;
  OsdiInitErrorPayload payload;
} OsdiInitError;

typedef struct OsdiInitInfo {
  uint32_t flags;
  uint32_t num_errors;
  OsdiInitError *errors;
} OsdiInitInfo;

/* 矩阵贡献位置：一对节点 */
typedef struct OsdiNodePair {
  uint32_t node_1;
  uint32_t node_2;
} OsdiNodePair;

/* 单个雅可比 entry：描述对矩阵哪个 (node1,node2) 位置贡献，及在实例数据块中的偏移 */
typedef struct OsdiJacobianEntry {
  OsdiNodePair nodes;
  uint32_t react_ptr_off;  /* 电抗性贡献在实例数据块中的偏移 */
  uint32_t flags;          /* JACOBIAN_ENTRY_* 标志 */
} OsdiJacobianEntry;

typedef struct OsdiNode {
  char *name;
  char *units;
  char *residual_units;
  uint32_t resist_residual_off;  /* 电阻性残差在实例块中的偏移 */
  uint32_t react_residual_off;   /* 电抗性残差在实例块中的偏移 */
  uint32_t resist_limit_rhs_off;
  uint32_t react_limit_rhs_off;
  bool is_flow;  /* true=电流节点(KCL), false=电压节点 */
} OsdiNode;

typedef struct OsdiParamOpvar {
  char **name;          /* 名字 + 别名数组 */
  uint32_t num_alias;
  char *description;
  char *units;
  uint32_t flags;       /* PARA_TY_* | PARA_KIND_* */
  uint32_t len;         /* 数组长度（标量为1） */
} OsdiParamOpvar;

typedef struct OsdiNoiseSource {
  char *name;
  OsdiNodePair nodes;
} OsdiNoiseSource;

/* 器件描述符：每个模型一个，含全部函数指针与元数据。
   这是 OSDI 的核心——仿真器拿到此结构即可驱动整个模型生命周期。 */
typedef struct OsdiDescriptor {
  char *name;           /* 模型名（如 "bsim4", "diode"） */

  uint32_t num_nodes;
  uint32_t num_terminals;
  OsdiNode *nodes;

  uint32_t num_jacobian_entries;
  OsdiJacobianEntry *jacobian_entries;

  uint32_t num_collapsible;
  OsdiNodePair *collapsible;
  uint32_t collapsed_offset;

  OsdiNoiseSource *noise_sources;
  uint32_t num_noise_src;

  uint32_t num_params;            /* 模型参数数 */
  uint32_t num_instance_params;   /* 实例参数数 */
  uint32_t num_opvars;            /* 工作点输出变量数 */
  OsdiParamOpvar *param_opvar;

  uint32_t node_mapping_offset;
  uint32_t jacobian_ptr_resist_offset;

  uint32_t num_states;
  uint32_t state_idx_off;

  uint32_t bound_step_offset;

  uint32_t instance_size;   /* 实例数据块字节数（malloc 用） */
  uint32_t model_size;      /* 模型数据块字节数 */

  /* 通用参数访问器：读写模型/实例参数 */
  void *(*access)(void *inst, void *model, uint32_t id, uint32_t flags);

  /* 模型初始化：分配 model_size 字节后调用，填入默认参数 */
  void (*setup_model)(void *handle, void *model, OsdiSimParas *sim_params,
                                       OsdiInitInfo *res);
  /* 实例初始化：分配 instance_size 字节后调用 */
  void (*setup_instance)(void *handle, void *inst, void *model,
                                       double temperature, uint32_t num_terminals,
                                       OsdiSimParas *sim_params, OsdiInitInfo *res);

  /* 核心：在工作点计算残差/雅可比/噪声/工作点变量，结果存入实例数据块。
     flags 控制(CALC_*)计算哪些量。返回 EVAL_RET_FLAG_*。 */
  uint32_t (*eval)(void *handle, void *inst, void *model, OsdiSimInfo *info);

  void (*load_noise)(void *inst, void *model, double freq, double *noise_dens);
  /* 从实例数据块取回已计算的残差，装配到全局 RHS 向量 dst */
  void (*load_residual_resist)(void *inst, void *model, double *dst);
  void (*load_residual_react)(void *inst, void *model, double *dst);
  void (*load_limit_rhs_resist)(void *inst, void *model, double *dst);
  void (*load_limit_rhs_react)(void *inst, void *model, double *dst);
  /* SPICE 兼容的便捷 RHS 加载（直接用 prev_solve）*/
  void (*load_spice_rhs_dc)(void *inst, void *model, double *dst, double *prev_solve);
  void (*load_spice_rhs_tran)(void *inst, void *model, double *dst,
                  double *prev_solve, double alpha);
  /* 从实例数据块取回已计算的雅可比，装配到全局矩阵（内部知道偏移）*/
  void (*load_jacobian_resist)(void *inst, void *model);
  void (*load_jacobian_react)(void *inst, void *model, double alpha);
  void (*load_jacobian_tran)(void *inst, void *model, double alpha);
} OsdiDescriptor;

#ifdef __cplusplus
} /* extern "C" */
#endif
