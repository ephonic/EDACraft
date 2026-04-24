# 8b10b Decoder Module Specification Document

## 1. Introduction

The **8b10b Decoder Module (decoder_8b10b)** is a high-speed digital block designed to convert 10-bit encoded words into their corresponding 8-bit symbols. This conversion is essential in serial communication protocols where 8b/10b encoding is used to ensure DC balance and facilitate clock recovery. The decoder supports both **control symbols** and **data symbols**, selecting the appropriate decoding path based on an external indicator. The design is optimized for synchronous operation with low latency.

## 2. Module Functionality

The decoder's primary function is to translate a 10-bit input into an 8-bit output while simultaneously determining whether the decoded output represents a data symbol or a control symbol. The key points of functionality include:

- **Symbol Identification:**  
  - **Control Symbols:** When the external `control_in` signal is asserted high, the module decodes the input using a predefined lookup table. This ensures that control characters (used for protocol management and synchronization) are correctly identified.  
  - **Data Symbols:** When `control_in` is low, the module performs data decoding, where the 10-bit word is processed by logical and arithmetic operations to generate a valid 8-bit data output.

- **Latency:**  
  - The output is updated with a single clock-cycle latency. All data capturing, combinational decoding, and output selection are pipelined to ensure high-speed operation.

### 2.1 Symbol Types

- **Control Symbols:**  
  Special synchronization and management symbols. When the `control_in` signal is high, the module employs a direct combinational lookup function to decode the input into a corresponding control word. Control symbols are critical for maintaining data stream integrity and protocol management.

- **Data Symbols:**  
  Standard 8-bit data values that have been transmitted as 10-bit encoded words. These symbols are detected when `control_in` is low. In addition to using direct lookup when applicable, an arithmetic logic network processes the input bits—performing bit-level comparisons and generating parity conditions—to produce the final 8-bit data word.

### 2.2 Data Symbol Decoding Rules

Data symbol decoding involves:
- **Segmentation and Processing:**  
  The 10-bit input is logically divided and processed. One decoding path uses a combinational function that maps specific 10-bit words to control outputs. Another path computes bit-level logic operations (via XOR, AND, OR combinations) to generate the final 8-bit output from the individual bits of the input.
  
- **Decoding Tables:**  
  Although the module uses a lookup function for several control-related code groups, it also relies on algorithmically derived parity and comparison signals. This approach is consistent with typical 5b/6b and 3b/4b decoding methods used in standard 8b/10b decoders, where:
  - The upper portion of the 10-bit word is generally associated with a 5b/6b decoding table.
  - The lower portion is mapped according to a 3b/4b decoding table.
  
  The module integrates these principles by combining results from the lookup function with additional combinational logic to verify and refine the decoded output.

## 3. Algorithm Overview

The decoding process is divided into two main paths corresponding to control and data symbols, determined by the `control_in` signal:

1. **Input Capture and Latching:**  
   - The module operates on a synchronous clock (`clk_in`) and supports an active-high asynchronous reset (`reset_in`).
   - When a valid input is detected on `decoder_valid_in`, the 10-bit encoded word is captured. This registered value is used in both the control decoding and the data symbol processing paths.
   
2. **Control Symbol Decoding Path:**  
   - When `control_in` is asserted, a combinational decoding function is executed. This function compares the 10-bit input to a series of predefined patterns corresponding to control characters.
   - For each matching pattern, the function produces a decoded 8-bit control symbol accompanied by an indicator that the symbol is a control character.
   - The final output for this path is provided on `decoder_out` and `control_out`, with the valid signal synchronized to the input via `decoder_valid_out`.

3. **Data Symbol Decoding Path:**  
   - For data symbols (when `control_in` is low), additional combinational logic takes effect.
   - Bit-level operations such as XOR, AND, OR, and parity checks are performed on the incoming 10-bit word. These operations mirror the functionality of conventional 5b/6b and 3b/4b decoding tables:
     - **5b/6b Decoding:** The higher-order bits are processed to generate 5 significant bits.
     - **3b/4b Decoding:** The lower-order bits are processed to yield 3 significant bits.
   - The results are then concatenated to form the final 8-bit data word.
   - This data path also registers control information indicative of the symbol type for downstream processing.

4. **Output Multiplexing:**  
   - A multiplexer selects between the two decoded outputs:
     - If `control_in` is high, the output from the control decoding path is forwarded.
     - Otherwise, the output from the data decoding path is selected.
   - The valid output signal (`decoder_valid_out`) and the control signal (`control_out`) are provided accordingly.

## 4. Module Interface

The following table summarizes the top-level ports of the 8b10b decoder module:

| **Port Name**         | **Direction** | **Width** | **Description**                                                                                                 |
|-----------------------|---------------|-----------|-----------------------------------------------------------------------------------------------------------------|
| **clk_in**            | Input         | 1 bit     | Rising edge triggered clock input.                                                                              |
| **reset_in**          | Input         | 1 bit     | Asynchronous active-high reset signal.                                                                          |
| **control_in**        | Input         | 1 bit     | Active HIGH Control symbol indicator. When high, indicates a control symbol; when low, indicates a data symbol. |
| **decoder_in**        | Input         | 10 bits   | The 10-bit encoded input word to be decoded.                                                                    |
| **decoder_valid_in**  | Input         | 1 bit     | Active HIGH Input valid signal. A high level indicates that the data on `decoder_in` is valid for decoding.     |
| **decoder_out**       | Output        | 8 bits    | The final 8-bit decoded output word.                                                                            |
| **decoder_valid_out** | Output        | 1 bit     | Active HIGH Output valid signal. Indicates that `decoder_out` and `control_out` reflect valid decoded data.     |
| **control_out**       | Output        | 1 bit     | Output control indicator. High when the decoded output corresponds to a control symbol and low for data symbols.|

## 5. Internal Architecture

To achieve its functionality, the design is partitioned into several key blocks and pipeline stages:

### 5.1 Input Capture and Latching

- **Registering the Input:**  
  When `decoder_valid_in` is asserted, the 10-bit input word is captured synchronously on the rising edge of `clk_in`. This registered value is used by both decoding paths, ensuring that the operations are performed on a stable data snapshot.
  
- **Valid Signal Generation:**  
  A dedicated pipeline register tracks the validity of the input data, propagating a valid flag which is used to synchronize downstream computations.

### 5.2 Control Symbol Decoding

- **Combinational Lookup Function:**  
  For control symbols, a combinational function (implemented using a case statement) maps the incoming 10-bit word directly to an 8-bit control code along with a control indicator.  
- **Output Selection:**  
  The results from this function are available immediately in the combinational domain and registered to be selected if `control_in` is high.

The decoder should support the control symbols, and special codes used for synchronization and control purposes and should decode them as follows.

| **10-bit Input**      | **8-bit Output** | **Symbol** | **DEC Value** | **HEX Value** |
|-----------------------|------------------|------------|---------------|---------------|
| 001111 0100           | 000 11100        | K.28.0     | 28            | 1C            |
| 110000 1011           | 000 11100        | K.28.0     | 28            | 1C            |
| 001111 1001           | 001 11100        | K.28.1     | 60            | 3C            |
| 110000 0110           | 001 11100        | K.28.1     | 60            | 3C            |
| 001111 0101           | 010 11100        | K.28.2     | 92            | 5C            |
| 110000 1010           | 010 11100        | K.28.2     | 92            | 5C            |
| 001111 0011           | 011 11100        | K.28.3     | 124           | 7C            |
| 110000 1100           | 011 11100        | K.28.3     | 124           | 7C            |
| 001111 0010           | 100 11100        | K.28.4     | 156           | 9C            |
| 110000 1101           | 100 11100        | K.28.4     | 156           | 9C            |
| 001111 1010           | 101 11100        | K.28.5     | 188           | BC            |
| 110000 0101           | 101 11100        | K.28.5     | 188           | BC            |
| 001111 0110           | 110 11100        | K.28.6     | 220           | DC            |
| 110000 1001           | 110 11100        | K.28.6     | 220           | DC            |
| 001111 1000           | 111 11100        | K.28.7     | 252           | FC            |
| 110000 0111           | 111 11100        | K.28.7     | 252           | FC            |
| 111010 1000           | 111 10111        | K.23.7     | 247           | F7            |
| 000101 0111           | 111 10111        | K.23.7     | 247           | F7            |
| 110110 1000           | 111 11011        | K.27.7     | 251           | FB            |
| 001001 0111           | 111 11011        | K.27.7     | 251           | FB            |
| 101110 1000           | 111 11101        | K.29.7     | 253           | FD            |
| 010001 0111           | 111 11101        | K.29.7     | 253           | FD            |
| 011110 1000           | 111 11110        | K.30.7     | 254           | FE            |
| 100001 0111           | 111 11110        | K.30.7     | 254           | FE            |

### 5.3 Data Symbol Decoding Logic

- **Bitwise Operations:**  
  The data decoding path employs a sequence of logical operations (XOR, AND, OR) on individual bits extracted from the 10-bit input. These operations effectively perform the role of translating the encoded 10-bit word into an 8-bit data symbol.  
- **Parity and Pattern Checking:**  
  Logical conditions are evaluated to derive parity signals, matching conditions, and candidate bit outputs analogous to the traditional 5b/6b and 3b/4b decoders.  
- **Final Data Assembly:**  
  The outputs from these operations are concatenated into the final 8-bit result for the data symbol and forwarded to the output multiplexer.

#### **5b/6b Decoding Table**

The MSB 6-bit of the 10-bit input is mapped back to its corresponding 5-bit (`EDCBA`).

| Encoded 6-bit (abcdei)       | Decoded 5-bit (EDCBA) |
|------------------------------|-----------------------|
| 100111, 011000               | 00000                 |
| 011101, 100010               | 00001                 |
| 101101, 010010               | 00010                 |
| 110001                       | 00011                 |
| 110101, 001010               | 00100                 |
| 101001                       | 00101                 |
| 011001                       | 00110                 |
| 111000, 000111               | 00111                 |
| 111001, 000110               | 01000                 |
| 100101                       | 01001                 |
| 010101                       | 01010                 |
| 110100                       | 01011                 |
| 001101                       | 01100                 |
| 101100                       | 01101                 |
| 011100                       | 01110                 |
| 010111, 101000               | 01111                 |
| 011011, 100100               | 10000                 |
| 100011                       | 10001                 |
| 010011                       | 10010                 |
| 110010                       | 10011                 |
| 001011                       | 10100                 |
| 101010                       | 10101                 |
| 011010                       | 10110                 |
| 111010, 000101               | 10111                 |
| 110011, 001100               | 11000                 |
| 100110                       | 11001                 |
| 010110                       | 11010                 |
| 110110, 001001               | 11011                 |
| 001110                       | 11100                 |
| 101110, 010001               | 11101                 |
| 011110, 100001               | 11110                 |
| 101011, 010100               | 11111                 |

#### **3b/4b Decoding Table**

The LSB 4-bit of the 10-bit input is mapped back to its corresponding 3-bit (`HGF`).

| Encoded 4-bit (fghj)         | Decoded 3-bit (HGF) |
|------------------------------|---------------------|
| 0100, 1011                   | 000                 |
| 1001                         | 001                 |
| 0101                         | 010                 |
| 0011, 1100                   | 011                 |
| 0010, 1101                   | 100                 |
| 1010                         | 101                 |
| 0110                         | 110                 |
| 1110, 0001                   | 111                 |


### 5.4 Output Multiplexing and Synchronization

- **Multiplexing Based on Symbol Type:**  
  A simple multiplexer selects the appropriate output:
  - **Control Path Selected:** When `control_in` is high, the pre-decoded control symbol and associated indicator are transmitted.
  - **Data Path Selected:** When `control_in` is low, the processed data symbol and its valid flag are forwarded.
  
- **Clock Domain Synchronization:**  
  The combined outputs are registered on the rising edge of the clock, ensuring that the `decoder_valid_out` signal is properly synchronized with the decoded data. The overall system latency is maintained at one clock cycle from valid input to valid output.

## 6. Timing and Latency

- **Synchronous Operation:**  
  All internal operations are triggered by the rising edge of `clk_in`. The asynchronous reset (`reset_in`) ensures that the internal state is immediately cleared when asserted.

- **Latency:**  
  The design ensures a fixed output latency of one clock cycle. This is accomplished by registering the input data and propagating the associated valid signal through the pipeline stages before it reaches the final output multiplexer.
  
- **Pipeline Considerations:**  
  Although the control decoding (via the lookup function) and the data path (via bit-level combinational logic) operate concurrently, both paths are synchronized to align their outputs. This guarantees that regardless of the symbol type, the final decoded word and the valid signal are updated simultaneously.



