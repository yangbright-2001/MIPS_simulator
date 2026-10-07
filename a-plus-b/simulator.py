import os
import sys

asm_code = sys.argv[1]
machine_code = sys.argv[2]
checkpoint_file = sys.argv[3]
input_file = sys.argv[4]
output_file = sys.argv[5]

op_code_dict = { '001000': 'addi',
            '001001': 'addiu',
            '001100': 'andi',
            '000100': 'beq',
            '000001': 'bgez',   #rt = 00001
            '000111': 'bgtz',   #rt = 00000
            '000110': 'blez',   #rt = 00000
            '000001': 'bltz',   #rt = 00000
            '000101': 'bne',
            '100000': 'lb',
            '100100': 'lbu',
            '100001': 'lh',
            '100101': 'lhu',
            '001111': 'lui',
            '100011': 'lw',
            '001101': 'ori',
            '101000': 'sb',
            '001010': 'slti',
            '001011': 'sltiu',
            '101001': 'sh',
            '101011': 'sw',
            '001110': 'xori',
            '100010': 'lwl',
            '100110': 'lwr',
            '101010': 'swl',
            '101110': 'swr',
            '000010': 'j',
            '000011': 'jal'
}

#function code for r-type
function_code_dict = {'100000': 'add',
                '100001': 'addu',
                '100100': 'and',
                '011010': 'div',
                '011011': 'divu',
                '001001': 'jalr',
                '001000': 'jr',
                '010000': 'mfhi',
                '010010': 'mflo',
                '010001': 'mthi',
                '010011': 'mtlo',
                '011000': 'mult',
                '011001': 'multu',
                '100111': 'nor',
                '100101': 'or',
                '000000': 'sll',
                '000100': 'sllv',
                '101010': 'slt',
                '101011': 'sltu',
                '000011': 'sra',
                '000111': 'srav',
                '000010': 'srl',
                '000110': 'srlv',
                '100010': 'sub',
                '100011': 'subu',
                '001100': 'syscall',
                '100110': 'xor'
}

memory_list = [0] * ( 6 * (2**18) )   #每4byte为一个单位存
register_list = [0] * 35  #35个register。每4byte为一个单位存，顺序是32+PC+HI+LO
register_list[28] = 5275648   #gp:0x508000
register_list[29] = 10485760  #sp:0xA00000
register_list[30] = 10485760  #sp:0XA00000
register_list[32] = 4194304   #pc:0x400000

in_file = open(input_file,'r')
out_file = open(output_file, 'w')

#dump memory and register
def dump(file_name, list_name):
    with open(file_name, 'wb') as f:
        for i in range(len(list_name)):
            #得分两种情况写，如果是负的，就要写signed=True
            #如果是正的就不用
            if list_name[i] >= 0:
                bin_data = int(list_name[i]).to_bytes(length = 4, byteorder = 'little')  #不能写signed = True， 不然会爆栈
            else:
                bin_data = int(list_name[i]).to_bytes(length = 4, byteorder = 'little', signed = True)
            f.write(bin_data)

def load_data(code, program_break):
    # program_break = int("500000",16)
    append_list = []        #每一个byte对应的数值
    pos_list = []       #每4个byte对应的数值
    if (code.find(".ascii") != -1): #ascii和asciiz
        quote_index = code.find("\"")  
        content = code[(quote_index + 1) : len(code) - 1] #去除了双引号和最后的\n,比如 “abc\n" 的长度是8，而不是7
        i = 0
        # print(content)
        # print(len(content))
        while i < len(content):
            # print(i, content[i])
            if (content[i] == "\\") and (content[i + 1] == "n") and ( i < (len(content) - 1) ):
                ascii = 10   #\n的ascii码
                append_list.append(ascii)
                i += 2
                continue
            else:
                ascii = ord(content[i])
                append_list.append(ascii)
                i += 1
        if (code.find(".asciiz") != -1):  #asciiz还要放一个\0在末尾
            append_list.append(0)
        complement = len(append_list) % 4
        if complement != 0:  #4个为一个block
            append_list += [0] * (4 - complement)
        num_pos = int( len(append_list) / 4 )
        for i in range(num_pos):
            #print(chr(append_list[4*i]),chr(append_list[4*i+1]), chr(append_list[4*i+2]), chr(append_list[4*i+3]), sep=" ")
            # num = append_list[4*i] * (16 ** 6) + append_list[4*i+1] * (16 ** 4) + append_list[4*i+2] * (16 ** 2) + append_list[4*i+3]
            num = append_list[4*i] + append_list[4*i+1] * (16 ** 2) + append_list[4*i+2] * (16 ** 4) + append_list[4*i+3] * (16 ** 6)
            # print(num)
            pos_list.append(num)
            program_break += 4
    
    elif (code.find(".half") != -1):
        # code_list = code.split()
        # halfword_list = code_list[2].split(",")
        code_list = code.split()
        all_halfword = code_list[2:]
        halfword_str = "".join(all_halfword)
        # print(halfword_str)
        halfword_list = halfword_str.split(",")
        # print(halfword_list)
        threshold = 15 * 16 + 15  
        for num in halfword_list:
            if int(num) <= threshold:    #能在1byte里面搞定
                append_list += [int(num), 0]
            else:
                high_pos = int(num) / 256
                low_pos = int(num) % 256
                append_list += [low_pos, high_pos]
        if ( len(halfword_list) % 2 != 0 ):
            append_list += [0]
        num_pos = int( len(append_list) / 4 )
        for i in range(num_pos):
            num = append_list[4*i] + append_list[4*i+1] * (16 ** 2) + append_list[4*i+2] * (16 ** 4) + append_list[4*i+3] * (16 ** 6)
            pos_list.append(num)
            program_break += 4
    
    elif (code.find(".byte") != -1):
        # code_list = code.split()
        # byte_list = code_list[2].split(",")
        code_list = code.split()
        all_byte = code_list[2:]
        byte_str = "".join(all_byte)
        # print(byte_str)
        byte_list = byte_str.split(",")
        # print(byte_list)
        for num in byte_list:
            append_list.append(int(num))
        complement = len(append_list) % 4
        if ( complement != 0 ):
            append_list += [0] * (4 - complement)
        num_pos = int( len(append_list) / 4 )
        for i in range(num_pos):
            num = append_list[4*i] + append_list[4*i+1] * (16 ** 2) + append_list[4*i+2] * (16 ** 4) + append_list[4*i+3] * (16 ** 6)
            pos_list.append(num)
            program_break += 4
    
    elif (code.find(".word") != -1):
        # code_list = code.split()
        # word_list = code_list[2].split(",")
        code_list = code.split()
        all_word = code_list[2:]
        word_str = "".join(all_word)
        # print(word_str)
        word_list = word_str.split(",")
        # print(word_list)
        for num in word_list:
            pos_list.append(int(num))
            program_break += 4
    
    return pos_list, program_break

def convert_2s_complement(num): #对象是二进制数字符串，这个数是对应的正数的二进制数，把整个二进制数转为补数
    num_list = list(num)
    for i in range((len(num_list) - 1),-1,-1):
        if (num_list[i] == '1'):
            break
    for j in range((i - 1), -1, -1):
        if (num_list[j] == '1'):
            num_list[j] = '0'
            continue
        elif (num_list[j] == '0'):
            num_list[j] = '1'
            continue            
    new_num = ''
    for i in range(len(num_list)):
        new_num = new_num + num_list[i]
    return new_num

def high_8(x):   #取最高8位
    x = ( ( ( (1<<8) - 1 ) << 24 ) & x ) >> 24
    return x

def high_mid_8(x):  #取24-16
    x = ( ( ( (1<<8) - 1 ) << 16 ) & x ) >> 16
    return x

def mid_low_8(x):   #取16-8
    x = ( ( ( (1<<8) - 1 ) << 8 ) & x ) >> 8
    return x

def low_8(x):   #取最低8
    x = ( (1<<8) - 1 ) & x
    return x

def low_16(x):
    x = x & ((1<<16)-1)
    return x

def high_16(x):
    x = ( ( ( (1<<16) - 1 ) << 16 ) & x ) >> 16
    return x

def to_unsign_int(bin_str):
    unsign_int = int(bin_str, 2)
    return unsign_int

def to_sign_int(bin_str):
    if bin_str[0] == "1":                      
        bin_str  = convert_2s_complement(bin_str)
        result = -int(bin_str,2)
    else:                                   
        result = int(bin_str,2)
    return result

####################    R-TYPE    ##############################################

def add(rd, rs, rt):   #把rd, rs, rt从machine code中拆出来
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    register_list[rd] = operand_1 + operand_2

def addu(rd, rs, rt):   #add不考虑overflow，那addu跟add就没区别了
    add(rd, rs, rt)

def and_mips(rd, rs, rt):  #直接&了，-9&5=5,希望register里面可以存和读取负数（比如直接读-9出来）
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    register_list[rd] = operand_1 & operand_2

def div(rs, rt):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    quotient = operand_1 // operand_2
    remainder = operand_1 % operand_2
    register_list[33] = remainder   #余数放在hi
    register_list[34] = quotient    #商放在lo

def divu(rs, rt):
    div(rs, rt)

def jalr(rd, rs, pc):    #算了,pc还是算跟0x400000的地址差/4吧。（从0开始走了多少个word）
    target_address = register_list[rs]
    register_list[rd] = int("400000", 16) + pc * 4 + 4   #pc是当前jalr的pc，所以再加4吧
    pc = ( target_address - int("400000", 16) ) // 4
    return pc

def jr(rs):
    target_address = register_list[rs]
    pc = ( target_address - int("400000", 16) ) // 4
    return pc

def mfhi(rd):
    data = register_list[33]
    register_list[rd] = data

def mflo(rd):
    data = register_list[34]
    register_list[rd] = data

def mthi(rs):
    data = register_list[rs]
    register_list[33] = data

def mtlo(rs):
    data = register_list[rs]
    register_list[34] = data

def mult(rs, rt):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    result = operand_1 * operand_2
    result_bin = bin(result)[2:]
    result_64 = '0' * ( 64 - len(result_bin) ) + result_bin  #转为64位
    store_hi = int(result_64[:32], 2)
    store_lo = int(result_64[32:64], 2)
    register_list[33] = store_hi    #hi存前32位     
    register_list[34] = store_lo    #lo存后32位

def multu(rs, rt):
    mult(rs, rt)

def nor(rd, rs, rt):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    register_list[rd] = ~(operand_1 | operand_2)

def or_mips(rd, rs, rt):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    register_list[rd] = (operand_1 | operand_2)

def sll(rd, rt, sa):
    data = register_list[rt]
    result = (data << sa)
    register_list[rd] = result

def sllv(rd, rt, rs):
    data = register_list[rt]
    shift_amount = register_list[rs]
    result = (data << shift_amount)
    register_list[rd] = result

def slt(rd, rs, rt):
    rs_value = register_list[rs]
    rt_value = register_list[rt]
    if rs_value < rt_value:
        register_list[rd] = 1
    else:
        register_list[rd] = 0

def sltu(rd, rs, rt):
    slt(rd, rs, rt)

def sra(rd, rt, sa):  #算术右移是按照最高位来决定是补0还是1
    data = register_list[rt]
    result = (data >> sa)    #>>运算符默认是会按照最高位补0的
    register_list[rd] = result

def srav(rd, rt, rs):
    data = register_list[rt]
    shift_amount = register_list[rs]
    result = (data >> shift_amount)
    register_list[rd] = result

def srl(rd, rt, sa):  #逻辑右移直接补0就行
    data = register_list[rt]
    if data < 0:
        data = -data  #先转为正的再说
        current_length = len( bin(data)[2:] )
        data = '0' * (32 - current_length) + bin(data)[2:]
        data = convert_2s_complement(data)
    else:
        current_length = len( bin(data)[2:] )
        data = '0' * (32 - current_length) + bin(data)[2:]
    data = sa * "0" + data  #逻辑右移直接补0就行
    data = data[:32]
    if data[0]=="0":
        register_list[rd] = int("0b" + data,2)
    else:
        data = convert_2s_complement(data)
        register_list[rd] = -int("0b" + data,2)

def srlv(rd, rt, rs):  
    data = register_list[rt]
    sa = register_list[rs]
    if data < 0:
        data = -data  #先转为正的再说
        current_length = len( bin(data)[2:] )
        data = '0' * (32 - current_length) + bin(data)[2:]
        data = convert_2s_complement(data)
    else:
        current_length = len( bin(data)[2:] )
        data = '0' * (32 - current_length) + bin(data)[2:]
    data = sa * "0" + data
    data = data[:32]
    if data[0]=="0":
        register_list[rd] = int("0b" + data, 2)
    else:
        data = convert_2s_complement(data)
        register_list[rd] = -int("0b" + data, 2)
        

def sub(rd, rs, rt):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    register_list[rd] = operand_1 - operand_2

def subu(rd, rs, rt):
    sub(rd, rs, rt)

def xor(rd, rs, rt):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    result = operand_1 ^ operand_2
    register_list[rd] = result

####################    I-TYPE    ##############################################

def addi(rt, rs, immediate):
    operand_1 = register_list[rs]
    register_list[rt] = operand_1 + immediate

def addiu(rt, rs, unsign_immediate):
    addi(rt, rs, unsign_immediate)

def andi(rt, rs, immediate):    #记得要提前把immediate转成2‘s complement再扔进来，转换方法可向ruirui学习
    operand_1 = register_list[rs]
    register_list[rt] = operand_1 & immediate

def beq(rs, rt, label, pc):  #label其实就是immediate
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    if operand_1 == operand_2:   #pc已经加好了，不用再统一自加了
        pc = pc + 1 + label
    else:
        pc += 1
    return pc

def bgez(rs, label, pc):
    data = register_list[rs]
    if data >= 0:
        pc = pc + 1 + label
    else:
        pc += 1
    return pc

def bgtz(rs, label, pc):
    data = register_list[rs]
    if data > 0:
        pc = pc + 1 + label
    else:
        pc += 1
    return pc

def blez(rs, label, pc):
    data = register_list[rs]
    if data <= 0:
        pc = pc + 1 + label
    else:
        pc += 1
    return pc

def bltz(rs, label, pc):
    data = register_list[rs]
    if data < 0:
        pc = pc + 1 + label
    else:
        pc += 1
    return pc

def bne(rs, rt, label, pc):
    operand_1 = register_list[rs]
    operand_2 = register_list[rt]
    if operand_1 != operand_2:
        pc = pc + 1 + label
    else:
        pc += 1
    return pc

def lb(rt, immediate, rs):   #lb指令的立即数不一定是4的倍数
    # base_address = register_list[rs]   #base address要从0x400000算起
    # relative_address = (base_address - int("400000", 16) )//4
    # quotient = immediate // 4
    # remainder = immediate % 4
    # word = memory_list[relative_address + quotient]

    base_address = register_list[rs]   #rs记录的是要从0算起的绝对地址
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4
    word = memory_list[quotient]

    # if immediate >= 0:
    #     if remainder == 0:  #取最高8位
    #         data = high_8(word)
    #         register_list[rt] = data
    #     elif remainder == 1:
    #         data = high_mid_8(word)
    #         register_list[rt] = data
    #     elif remainder == 2:
    #         data = mid_low_8(word)
    #         register_list[rt] = data
    #     elif remainder == 3:
    #         data = low_8(word)
    #         register_list[rt] = data
    # else:
    #     if remainder == 0:
    #         data = high_8(word)
    #         register_list[rt] = data
    #     elif remainder == 1:
    #         data = high_mid_8(word)
    #         register_list[rt] = data
    #     elif remainder == 2:
    #         data = mid_low_8(word)
    #         register_list[rt] = data
    #     elif remainder == 2:
    #         data = low_8(word)
    #         register_list[rt] = data

    #######################################################
    if remainder == 0:  #取最高8位
        # data = high_8(word)
        data = low_8(word)
        register_list[rt] = data 
    elif remainder == 1:
        # data = high_mid_8(word)
        data = mid_low_8(word)
        register_list[rt] = data
    elif remainder == 2:
        # data = mid_low_8(word)
        data = high_mid_8(word)
        register_list[rt] = data
    elif remainder == 3:
        # data = low_8(word)
        data = high_8(word)
        register_list[rt] = data

def lbu(rt, unsign_immediate, rs):
    lb(rt, unsign_immediate, rs)

def lh(rt, immediate, rs):
    # base_address = register_list[rs]   #base address要从0x400000算起
    # relative_address = (base_address - int("400000", 16) )//4
    # quotient = immediate // 4
    # remainder = immediate % 4
    # word = memory_list[relative_address + quotient]

    base_address = register_list[rs]   #rs记录的是要从0算起的绝对地址
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4
    word = memory_list[quotient]

    # if immediate >= 0:
    #     if remainder == 0:  #取最高8位
    #         data = high_16(word)
    #         data = (mid_low_8(data)) + (low_8(data)<<8)
    #         register_list[rt] = data
    #     elif remainder == 2:
    #         data = low_16(word)
    #         data = (mid_low_8(data)) + (low_8(data)<<8)
    #         register_list[rt] = data
    # else:
    #     if remainder == 0:
    #         data = high_16(word)
    #         data = (mid_low_8(data)) + (low_8(data)<<8)
    #         register_list[rt] = data
    #     elif remainder == 2:
    #         data = low_16(word)
    #         data = (mid_low_8(data)) + (low_8(data)<<8)
    #         register_list[rt] = data

    ###################################################################
    if remainder == 0:  
        # data = high_16(word)
        # data = (mid_low_8(data)) + (low_8(data)<<8)
        data = low_16(word)
        # data = (mid_low_8(data) << 8) + (low_8(data))
        register_list[rt] = data
    elif remainder == 2:
        # data = low_16(word)
        # data = (mid_low_8(data)) + (low_8(data)<<8)
        data = high_16(word)
        # data = (mid_low_8(data) << 8) + (low_8(data))
        register_list[rt] = data

def lhu(rt, unsign_immediate, rs):
    lh(rt, unsign_immediate, rs)

def lui(rt, bin_immediate):
    str = bin_immediate + '0' * 16
    if str[0] == '1':
        str = convert_2s_complement(str)
        data = -int("0b"+str, 2)
        register_list[rt] = data
    else:
        data = int("0b"+str, 2)
        register_list[rt] = data

def lw(rt, immediate, rs):
    base_address = register_list[rs]   #base address要从0x400000算起
    relative_address = (base_address - int("400000", 16) )//4
    quotient = immediate // 4
    data = memory_list[relative_address + quotient]
    register_list[rt] = data

def ori(rt, rs, unsign_immediate):
    operand_1 = register_list[rs]
    register_list[rt] = operand_1 | unsign_immediate

def sb(rt, immediate, rs):      #store the low byte from rt
    data_to_store = low_8(register_list[rt])  #取rt中的最low byte

    base_address = register_list[rs]   #base address要从0x400000算起
    # print("register[rs]=", base_address)
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4

    #######################################################################
    if remainder == 0:
        # memory_list[quotient] = data_to_store << 24  
        memory_list[quotient] = data_to_store   
    elif remainder == 1:
        # memory_list[quotient] = data_to_store << 16 
        memory_list[quotient] = data_to_store << 8 
    elif remainder == 2:
        # memory_list[quotient] = data_to_store << 8
        memory_list[quotient] = data_to_store << 16
    elif remainder == 3:
        # memory_list[quotient] = data_to_store 
        memory_list[quotient] = data_to_store << 24

def slti(rt, rs, immediate):
    operand_1 = register_list[rs]
    if operand_1 < immediate:
        register_list[rt] = 1
    else:
        register_list[rt] = 0

def sltiu(rt, rs, unsign_immediate):
    slti(rt, rs, unsign_immediate)

def sh(rt, immediate, rs):
    data_to_store = low_16(register_list[rt])  #取rt中的最low byte

    base_address = register_list[rs]   #base address要从0x400000算起
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4

    ######################################################################
    if remainder == 0:
        # memory_list[quotient] = (low_8(data_to_store)<<24) + (low_mid_8(data_to_store)<<16)
        memory_list[quotient] = data_to_store
    elif remainder == 2:      
        # memory_list[quotient] = (low_8(data_to_store)<<8) + (low_mid_8(data_to_store))
        memory_list[quotient] = (low_8(data_to_store)<<24) + (mid_low_8(data_to_store)<<16)

def sw(rt, immediate, rs):
    data_to_store = register_list[rt]

    base_address = register_list[rs]   #base address要从0x400000算起
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4
    memory_list[quotient] = data_to_store
    
def xori(rt, rs, unsign_immediate):
    operand_1 = register_list[rs]
    result = unsign_immediate ^ operand_1
    register_list[rt] = result

def lwl(rt, immediate, rs): #load the left bytes from the word
    base_address = register_list[rs]   #rs记录的是要从0算起的绝对地址
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4
    word = memory_list[quotient]
    print(word)

    print("remainder = ", remainder)

    ######################################################################
    if remainder == 0:
        save_part = (low_8(word)<<24) 
        print(save_part)
        data = save_part + (mid_low_8(register_list[rt])<<16) + (high_mid_8(register_list[rt])<<8) + (high_8(register_list[rt]))
        # print(register_list[rt])
        # print(mid_low_8(register_list[rt])<<16)
        # print(high_mid_8(register_list[rt])<<8)
        # print(high_8(register_list[rt]))
        # print("data = ", data)
        # save_part = high_8(word) 
        # data = save_part + (high_mid_8(register_list[rt])<<8) + (mid_low_8(register_list[rt])<<16) + (low_8(register_list[rt])<<24)
        register_list[rt] = data
    elif remainder == 1:
        save_part = (low_8(word)<<16) + (mid_low_8(word)<<24) 
        data = save_part + (high_mid_8(register_list[rt])<<8) + (high_8(register_list[rt]))
        print("data = ", data)
        # save_part = high_8(word) + (high_mid_8(word)<<8)
        # data = save_part + (mid_low_8(register_list[rt])<<16) + (low_8(register_list[rt])<<24)
        register_list[rt] = data
    elif remainder == 2:
        save_part = (low_8(word)<<8) + (mid_low_8(word)<<16) + (high_mid_8(word)<<24) 
        data = save_part + (high_8(register_list[rt]))
        print("data = ", data)
        # save_part = (high_8(word)) + (high_mid_8(word)<<8) + (mid_low_8(word)<<16) 
        # data = save_part + (low_8(register_list[rt])<<24)
        register_list[rt] = data
    elif remainder == 3:
        save_part = (low_8(word)) + (mid_low_8(word)<<8) + (high_mid_8(word)<<16) + (high_8(word)<<24) 
        data = save_part
        print("data = ", data)
        # save_part = (high_8(word)) + (high_mid_8(word)<<8) + (mid_low_8(word)<<16) + (low_8(word)<<24) 
        # data = save_part
        register_list[rt] = data

def lwr(rt, immediate, rs): #load the right bytes from the word
    base_address = register_list[rs]   #rs记录的是要从0算起的绝对地址
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4
    word = memory_list[quotient]

    print("remainder = ", remainder)

    ##################################################################
    if remainder == 0:
        # save_part = (high_8(word)<<24) 
        # data = save_part + (high_mid_8(register_list[rt])<<16) + (mid_low_8(register_list[rt])<<8) + (low_8(register_list[rt]))
        save_part = (low_8(word)) + (mid_low_8(word)<<8) + (high_mid_8(word)<<16) + (high_8(word)<<24) 
        data = save_part
        register_list[rt] = data
    elif remainder == 1:
        # save_part = (high_8(word)<<16) + (high_mid_8(word)<<24) 
        # data = save_part + (mid_low_8(register_list[rt])<<8) + (low_8(register_list[rt]))
        save_part = (mid_low_8(word)) + (high_mid_8(word)<<8) + (high_8(word)<<16) 
        print(save_part)
        data = save_part + (low_8(register_list[rt])<<24)
        print("register_list[rt]=",register_list[rt])
        print("data = ", data)
        register_list[rt] = data
    elif remainder == 2:
        # save_part = (high_8(word)<<8) + (high_mid_8(word)<<16) + (mid_low_8(word)<<24) 
        # data = save_part + (low_8(register_list[rt]))
        save_part = (high_mid_8(word)) + (high_8(word)<<8) 
        data = save_part + (low_8(register_list[rt])<<24) + (mid_low_8(register_list[rt])<<16)
        register_list[rt] = data
    elif remainder == 3:
        # save_part = (high_8(word)) + (high_mid_8(word)<<8) + (mid_low_8(word)<<16) + (low_8(word)<<24) 
        # data = save_part
        save_part = high_8(word)
        data = save_part + (low_8(register_list[rt])<<24) + (mid_low_8(register_list[rt])<<16) + (high_mid_8(register_list[rt])<<8)
        register_list[rt] = data

def swl(rt, immediate, rs):
    base_address = register_list[rs]   #rs记录的是要从0算起的绝对地址
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4

    word = register_list[rt]

    print("remainder = ", remainder)

    ########################################################################
    if remainder == 0:
        save_part = (low_8(word)<<24) 
        data = save_part + (mid_low_8(memory_list[quotient])<<16) + (high_mid_8(memory_list[quotient])<<8) + (high_8(memory_list[quotient]))
        # save_part = high_8(word) 
        # data = save_part + (high_mid_8(memory_list[quotient])<<8) + (mid_low_8(memory_list[quotient])<<16) + (low_8(memory_list[quotient])<<24)
        memory_list[quotient] = data
    elif remainder == 1:
        save_part = (low_8(word)<<16) + (mid_low_8(word)<<24) 
        data = save_part + (high_mid_8(memory_list[quotient])<<8) + (high_8(memory_list[quotient]))
        # save_part = high_8(word) + (high_mid_8(word)<<8)
        # data = save_part + (mid_low_8(memory_list[quotient])<<16) + (low_8(memory_list[quotient])<<24)
        memory_list[quotient] = data
    elif remainder == 2:
        save_part = (low_8(word)<<8) + (mid_low_8(word)<<16) + (high_mid_8(word)<<24) 
        data = save_part + (high_8(memory_list[quotient]))
        # save_part = (high_8(word)) + (high_mid_8(word)<<8) + (mid_low_8(word)<<16) 
        # data = save_part + (low_8(memory_list[quotient])<<24)
        memory_list[quotient] = data
    elif remainder == 3:
        save_part = (low_8(word)) + (mid_low_8(word)<<8) + (high_mid_8(word)<<16) + (high_8(word)<<24) 
        data = save_part
        # save_part = (high_8(word)) + (high_mid_8(word)<<8) + (mid_low_8(word)<<16) + (low_8(word)<<24) 
        # data = save_part
        memory_list[quotient] = data

def swr(rt, immediate, rs): #save the right bytes from the word
    base_address = register_list[rs]   #rs记录的是要从0算起的绝对地址
    relative_address = base_address + immediate - int("400000", 16)  #相对地址 = 绝对地址 - 0x400000
    quotient = relative_address // 4   
    remainder = relative_address % 4

    word = register_list[rt]

    print("remainder = ", remainder)
    
    ####################################################################
    if remainder == 0:
        # save_part = (high_8(word)<<24) 
        # data = save_part + (high_mid_8(register_list[rt])<<16) + (mid_low_8(register_list[rt])<<8) + (low_8(register_list[rt]))
        save_part = (low_8(word)) + (mid_low_8(word)<<8) + (high_mid_8(word)<<16) + (high_8(word)<<24) 
        data = save_part
        memory_list[quotient] = data
    elif remainder == 1:
        # save_part = (high_8(word)<<16) + (high_mid_8(word)<<24) 
        # data = save_part + (mid_low_8(register_list[rt])<<8) + (low_8(register_list[rt]))
        save_part = (mid_low_8(word)) + (high_mid_8(word)<<8) + (high_8(word)<<16) 
        data = save_part + (low_8(memory_list[quotient])<<24)
        memory_list[quotient] = data
    elif remainder == 2:
        # save_part = (high_8(word)<<8) + (high_mid_8(word)<<16) + (mid_low_8(word)<<24) 
        # data = save_part + (low_8(register_list[rt]))
        save_part = (high_mid_8(word)) + (high_8(word)<<8) 
        data = save_part + (low_8(memory_list[quotient])<<24) + (mid_low_8(memory_list[quotient])<<16)
        memory_list[quotient] = data
    elif remainder == 3:
        # save_part = (high_8(word)) + (high_mid_8(word)<<8) + (mid_low_8(word)<<16) + (low_8(word)<<24) 
        # data = save_part
        save_part = (high_8(word)) 
        data = save_part + (low_8(memory_list[quotient])<<24) + (mid_low_8(memory_list[quotient])<<16) + (high_mid_8(memory_list[quotient])<<8)
        memory_list[quotient] = data

####################    J-TYPE    ##############################################

def j(bin_label, pc):  #label喂进来的时候就是个整数
    # bin_label = bin(label)[2:] 
    # label_26 = '0' * (26 - len(bin_label)) + bin_label
    pc_address = int("400000", 16) + pc * 4
    bin_pc = bin(pc_address)[2:]
    pc_32 = '0' * (32 - len(bin_pc)) + bin_pc
    # new_pc = pc_32[:4] + label_26 + '00'
    new_pc_address = pc_32[:4] + bin_label + '00'
    new_pc_address = int(new_pc_address,2)
    new_pc = ( new_pc_address - int("400000", 16) ) // 4
    return new_pc

def jal(bin_label, pc):
    pc_address = int("400000", 16) + pc * 4
    next_instruction = pc_address + 4
    register_list[31] = next_instruction
    bin_pc = bin(pc_address)[2:]
    pc_32 = '0' * (32 - len(bin_pc)) + bin_pc
    # new_pc = pc_32[:4] + label_26 + '00'
    new_pc_address = pc_32[:4] + bin_label + '00'
    new_pc_address = int(new_pc_address, 2)
    new_pc = ( new_pc_address - int("400000", 16) ) // 4
    return new_pc

####################    syscall    ##############################################

def syscall(time, exit_flag, program_break):

    mode_number = register_list[2]

    if mode_number == 1:
        num = register_list[4]
        print("time ", time+1, ": ", num)
        out_file.write(str(num))
    
    elif mode_number == 4:
        stop_flag = False
        index = 0
        #a0里存的是绝对地址
        start_relative_address = ( register_list[4] - int("400000",16) ) // 4
        remainder = ( register_list[4] - int("400000",16) ) % 4  #起始地址不一定是四的整数倍
        # print("time=",time-1)
        # print("register_list[4]",register_list[4])
        # print("#################################")
        # print("register_list[4] - int(\"400000\",16)=",register_list[4] - int("400000",16))
        # print("remainder=",remainder)
        content = ""
        while stop_flag == False:
            # content = ""
            if remainder == 0:
                data = memory_list[start_relative_address + index]
                # print("data is int is ", data)
                # print("data in binary is ",bin(data))
                char_1 = chr( low_8(data) )
                # print("high-8 is ",bin(high_8(data))[2:])
                char_2 = chr( mid_low_8(data) )
                # print("mid_8 is ",bin(high_mid_8(data))[2:])
                char_3 = chr( high_mid_8(data) )
                char_4 = chr( high_8(data) )
            elif remainder == 1:
                data = memory_list[start_relative_address + index]
                char_1 = chr( mid_low_8(data) )
                char_2 = chr( high_mid_8(data) )
                char_3 = chr( high_8(data) )
                data = memory_list[start_relative_address + 1 + index]
                char_4 = chr( low_8(data) )
            elif remainder == 2:
                data = memory_list[start_relative_address + index]
                char_1 = chr( high_mid_8(data) )
                char_2 = chr( high_8(data) )
                data = memory_list[start_relative_address + 1 + index]
                char_3 = chr( low_8(data) )
                char_4 = chr( mid_low_8(data) )
            elif remainder == 3:
                data = memory_list[start_relative_address + index]
                char_1 = chr( high_8(data) )
                data = memory_list[start_relative_address + 1 + index]
                char_2 = chr( low_8(data) )
                char_3 = chr( mid_low_8(data) )
                char_4 = chr( high_mid_8(data) )
            char_list = [char_1, char_2, char_3, char_4]
            for char in char_list:
            
            ###########################################################################
                if char == "\0":
                # if char == "\0" or char == "\n":
                    stop_flag = True
                else:
                    content += char
                    # print(char)
                    # out_file.write(char)
            # print(content)
            # out_file.write(content)
            index += 1
        out_file.write(content)
        # print(time, " ", content)
    
    elif mode_number == 5:       #也看到有人用read_index
        data = in_file.readline()
        data = data.replace("\n","")
        data = data.strip()
        register_list[2] = int(data)

    elif mode_number == 8:
        buffer_address = register_list[4]   #依然是绝对地址
        length = register_list[5]
        data = in_file.readline()

        #############################################################################
        data = data.replace("\n","")

        if len(data) >= length:
            data = data[:length]
        quotient = ( buffer_address - int("400000", 16) )//4
        remainder = ( buffer_address - int("400000", 16) )%4
        length = len(data)
        offset = length % 4

        if remainder == 0:
            index = 0            
            while length > 0: 
                if length >= 4:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    char_4 = ord(data[4*index + 3])
                    ##################################################################################
                    memory_list[quotient + index] = char_1 + (char_2 << 8) + (char_3 << 16) + (char_4 << 24)
                    length = length - 4
                    index += 1
                elif length == 3:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    word = memory_list[quotient + index]
                    memory_list[quotient + index] = char_1 + (char_2 << 8) + (char_3 << 16) + (low_8(word) << 24)
                    length = length - 3
                elif length == 2:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    word = memory_list[quotient + index]
                    memory_list[quotient + index] = char_1 + (char_2 << 8) + (mid_low_8(word) << 16) +(low_8(word) << 24)
                    length = length - 2
                elif length == 1:
                    char_1 = ord(data[4*index])
                    word = memory_list[quotient + index]
                    memory_list[quotient + index] = char_1 + (high_mid_8(word) << 8) + (mid_low_8(word) << 16) + (low_8(word) << 24)
                    length = length - 2
        
        elif remainder == 1:
            index = 0            
            while length > 0: 
                if length >= 4:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    char_4 = ord(data[4*index + 3])
                    word_1 = memory_list[quotient + index]
                    word_2 = memory_list[quotient + index + 1]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (char_1 << 8) + (char_2 << 16) + (char_3 << 2)
                    memory_list[quotient + index + 1] = char_4 + (high_mid_8(word_2) << 8) + (mid_low_8(word_2) << 16) + (low_8(word_2) << 24)
                    length = length - 4
                    index += 1
                elif length == 3:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    word_1 = memory_list[quotient + index]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (char_1 << 8) + (char_2 << 16) + (char_3 << 24)
                    length = length - 3
                elif length == 2:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    word_1 = memory_list[quotient + index]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (char_1 << 8) + (char_2 << 16) + (low_8(word_1) << 24)
                    length = length - 2
                elif length == 1:
                    char_1 = ord(data[4*index])
                    word_1 = memory_list[quotient + index]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (char_1 << 8) + (mid_low_8(word_1) << 16) + (low_8(word_1) << 24)
                    length = length - 1
        
        elif remainder == 2:
            index = 0            
            while length > 0: 
                if length >= 4:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    char_4 = ord(data[4*index + 3])
                    word_1 = memory_list[quotient + index]
                    word_2 = memory_list[quotient + index + 1]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (char_1 << 16) + (char_2 << 24)
                    memory_list[quotient + index + 1] = char_3 + (char_4 << 8) + (mid_low_8(word_2) << 16) + (low_8(word_2) << 24)
                    length = length - 4
                    index += 1
                elif length == 3:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    word_1 = memory_list[quotient + index]
                    word_2 = memory_list[quotient + index + 1]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (char_1 << 16) + (char_2 << 24)
                    memory_list[quotient + index + 1] = char_3 + (high_mid_8(word_2) << 8) + (mid_low_8(word_2) << 16) + (low_8(word_2) << 24)
                    length = length - 3
                elif length == 2:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    word_1 = memory_list[quotient + index]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (char_1 << 16) + (char_2 << 24)
                    length = length - 2
                elif length == 1:
                    char_1 = ord(data[4*index])
                    word_1 = memory_list[quotient + index]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (char_1 << 16) + (low_8(word_1) << 24)
                    length = length - 1
        
        elif remainder == 3:
            index = 0            
            while length > 0: 
                if length >= 4:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    char_4 = ord(data[4*index + 3])
                    word_1 = memory_list[quotient + index]
                    word_2 = memory_list[quotient + index + 1]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (mid_low_8(word_1) << 16) + (char_1 << 24)
                    memory_list[quotient + index + 1] = char_2 + (char_3 << 8) + (char_4 << 16) + (low_8(word_2) << 24)
                    length = length - 4
                    index += 1
                elif length == 3:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    char_3 = ord(data[4*index + 2])
                    word_1 = memory_list[quotient + index]
                    word_2 = memory_list[quotient + index + 1]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (mid_low_8(word_1) << 16) + (char_1 << 24)
                    memory_list[quotient + index + 1] = char_2 + (char_3 << 8) + (mid_low_8(word_2) << 16) + (low_8(word_2) << 24)
                    length = length - 3
                elif length == 2:
                    char_1 = ord(data[4*index])
                    char_2 = ord(data[4*index + 1])
                    word_1 = memory_list[quotient + index]
                    word_2 = memory_list[quotient + index + 1]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (mid_low_8(word_1)<< 16) + (char_1 << 24)
                    memory_list[quotient + index + 1] = char_2 + (high_mid_8(word_2) << 8) + (mid_low_8(word_2) << 16) + (low_8(word_2) << 24)
                    length = length - 2
                elif length == 1:
                    char_1 = ord(data[4*index])
                    word_1 = memory_list[quotient + index]
                    ##################################################################################
                    memory_list[quotient + index] = high_8(word_1) + (high_mid_8(word_1) << 8) + (char_1 << 16) + (low_8(word_1) << 24)
                    length = length - 1
    
    elif mode_number == 9:
        shift_amount = register_list[4]
        register_list[2] = program_break   #the next position so that we can put stuff in 
        # print("program_break = ", program_break)
        program_break += shift_amount   #update the program break (top of data segment)
    
    elif mode_number == 10:
        exit_flag = True
        # sys.exit()
    
    elif mode_number == 11:
        data = register_list[4]
        char = chr(data)
        out_file.write(char)
    
    elif mode_number == 12:
        char = in_file.readline()
        char = char.replace("\n","")
        char = char.strip()
        data = ord(char)
        register_list[2] = data
    
    elif mode_number == 13:
        file_name_address = register_list[4]
        open_flag = register_list[5]
        open_mode = register_list[6]
        start_relative_address = ( file_name_address - int("400000",16) ) // 4
        remainder = ( file_name_address - int("400000",16) ) % 4  #起始地址不一定是四的整数倍

        file_name = ""

        stop_flag = False
        index = 0
        #获取标题的名字，方法同1
        while stop_flag == False:
            if remainder == 0:
                data = memory_list[start_relative_address + index]
                char_1 = chr( low_8(data) )
                char_2 = chr( mid_low_8(data) )
                char_3 = chr( high_mid_8(data) )
                char_4 = chr( high_8(data) )
            elif remainder == 1:
                data = memory_list[start_relative_address + index]
                char_1 = chr( mid_low_8(data) )
                char_2 = chr( high_mid_8(data) )
                char_3 = chr( high_8(data) )
                data = memory_list[start_relative_address + 1 + index]
                char_4 = chr( low_8(data) )
            elif remainder == 2:
                data = memory_list[start_relative_address + index]
                char_1 = chr( high_mid_8(data) )
                char_2 = chr( high_8(data) )
                data = memory_list[start_relative_address + 1 + index]
                char_3 = chr( low_8(data) )
                char_4 = chr( mid_low_8(data) )
            elif remainder == 3:
                data = memory_list[start_relative_address + index]
                char_1 = chr( high_8(data) )
                data = memory_list[start_relative_address + 1 + index]
                char_2 = chr( high_mid_8(data) )
                char_3 = chr( mid_low_8(data) )
                char_4 = chr( high_mid_8(data) )
            char_list = [char_1, char_2, char_3, char_4]
            for char in char_list:            
            ###########################################################################
                if char == "\0":
                # if char == "\0" or char == "\n":
                    stop_flag = True
                    break
                else:
                    file_name += char
            index += 1
            ##########################################################################
        # print("file name is: ", file_name)
        # print("open flag is: ", open_flag) 
        # print("open mode is: ", open_mode)
        # fd = os.open(file_name, open_flag, open_mode)     #最开始写的
        fd = os.open(file_name,os.O_RDWR|os.O_CREAT )
        register_list[4] = fd

    elif mode_number == 14:
        file_descriptor = register_list[4]
        buffer_address = register_list[5]
        mode = register_list[6]
        data = os.read(file_descriptor, mode).decode()
        length = len(data)
        register_list[4] = length
        
        quotient = ( buffer_address - int("400000",16) ) // 4
        remainder = ( buffer_address - int("400000",16) ) % 4  #起始地址不一定是四的整数倍

        #把内容读到memory去，同8
        # if remainder == 0:  
        index = 0            
        while length > 0: 
            if length >= 4:
                char_1 = ord(data[4*index])
                char_2 = ord(data[4*index + 1])
                char_3 = ord(data[4*index + 2])
                char_4 = ord(data[4*index + 3])
                ##################################################################################
                memory_list[quotient + index] = char_1 + (char_2 << 8) + (char_3 << 16) + (char_4 << 24)
                length = length - 4
                index += 1
            elif length == 3:
                char_1 = ord(data[4*index])
                char_2 = ord(data[4*index + 1])
                char_3 = ord(data[4*index + 2])
                word = memory_list[quotient + index]
                memory_list[quotient + index] = char_1 + (char_2 << 8) + (char_3 << 16) + (low_8(word) << 24)
                length = length - 3
            elif length == 2:
                char_1 = ord(data[4*index])
                char_2 = ord(data[4*index + 1])
                word = memory_list[quotient + index]
                memory_list[quotient + index] = char_1 + (char_2 << 8) + (mid_low_8(word) << 16) +(low_8(word) << 24)
                length = length - 2
            elif length == 1:
                char_1 = ord(data[4*index])
                word = memory_list[quotient + index]
                memory_list[quotient + index] = char_1 + (high_mid_8(word) << 8) + (mid_low_8(word) << 16) + (low_8(word) << 24)
                length = length - 1
        
        ###############################################绷不住了，不想写这么多情况#############################################
       
    
    if mode_number == 15:
        file_descriptor = register_list[4]
        buffer_address = register_list[5]
        length = register_list[6]
        # print("maximum length = ", length)

        start_relative_address = ( buffer_address - int("400000",16) ) // 4
        remainder = ( buffer_address - int("400000",16) ) % 4  #起始地址不一定是四的整数倍
        # print("remainder = ", remainder)
        file_content = ""
        stop_flag = False

        ###############################################绷不住了，不想写这么多情况#############################################
        # if remainder == 0:
        index = 0
        while stop_flag == False:
            if length >= 4:
                data = memory_list[start_relative_address + index]
                char_1 = chr( low_8(data) )
                char_2 = chr( mid_low_8(data) )
                char_3 = chr( high_mid_8(data) )
                char_4 = chr( high_8(data) )
                char_list = [char_1, char_2, char_3, char_4]
                for char in char_list:            
                ###########################################################################
                    if char == "\0":
                    # if char == "\0" or char == "\n":
                        file_content += char    #\0也要打进去,面向结果编程。。
                        stop_flag = True
                        break
                    else:
                        file_content += char
                index += 1
                length -= 4
            elif length == 3:
                data = memory_list[start_relative_address + index]
                char_1 = chr( low_8(data) )
                char_2 = chr( mid_low_8(data) )
                char_3 = chr( high_mid_8(data) )
                char_list = [char_1, char_2, char_3, char_4]
                for char in char_list:            
                ###########################################################################
                    if char == "\0":
                    # if char == "\0" or char == "\n":
                        file_content += char    #\0也要打进去,面向结果编程。。
                        stop_flag = True
                        break
                    else:
                        file_content += char
                index += 1
                stop_flag = True
            elif length == 2:
                data = memory_list[start_relative_address + index]
                char_1 = chr( low_8(data) )
                char_2 = chr( mid_low_8(data) )
                char_list = [char_1, char_2]
                for char in char_list:            
                ###########################################################################
                    if char == "\0":
                    # if char == "\0" or char == "\n"
                        file_content += char    #\0也要打进去,面向结果编程。。
                        stop_flag = True
                        break
                    else:
                        file_content += char
                index += 1
                stop_flag = True
            elif length == 1:
                data = memory_list[start_relative_address + index]
                char_1 = chr( low_8(data) )
                char_list = [char_1]
                for char in char_list:            
                ###########################################################################
                    if char == "\0":
                    # if char == "\0" or char == "\n":
                        file_content += char    #\0也要打进去,面向结果编程。。
                        stop_flag = True
                        break
                    else:
                        file_content += char
                index += 1
                stop_flag = True
        # print(file_content)
        actual_length = len(file_content)
        # print("actual_length = ", actual_length)
        # print("file_content[0] = ",ord(file_content[0]))
        # print("file_content[39] = ",file_content[39])
        register_list[4] = actual_length
        os.write(file_descriptor, file_content.encode())

    elif mode_number == 16:
        file_descriptor = register_list[4]
        os.close(file_descriptor)
    
    elif mode_number == 17:
        exit_flag = True
        # sys.exit()
    
    return program_break, exit_flag


#把machine code读进memory
with open(machine_code, 'r') as f:
    code_list = f.readlines()
# print(type(code_list[0][:32]))
# print(ord(code_list[0][32]))
for i in range(len(code_list)):
    code = int(code_list[i],2)
    memory_list[i] = code

#读checkpoint
with open(checkpoint_file, 'r') as f:
    checkpoint_list = f.readlines()
checkpoint_list = [int(i) for i in checkpoint_list]

#读入.data
with open(asm_code, 'r') as f:
    asm_list = f.readlines()
data_list = []
data_flag = False
program_break = int("500000",16)
for code in asm_list:
    code = code.strip()
    if (code == ''):
        continue
    if (code.find("#") == 0):
        continue
    if "#" in code:  #去除comments
        code = code[:code.find('#')]
        code = code.strip()
    if ".data" in code:
        data_flag = True
        continue

    if (data_flag == True):   
        # pos_list, program_break = load_data(code)
        pos_list, program_break = load_data(code, program_break)
        # print("program_break after load data:", program_break)
        data_list += pos_list
        for i in range(len(data_list)):
            memory_list[2 ** 18 + i] = data_list[i]
    
    if ".text" in code:
        data_flag = False
        break

#开始处理.text
# for code in code_list:
exit_flag = False
time = 0
pc = 0
while exit_flag == False:
    if time in checkpoint_list:
        register_file_name = "register_" + str(time) + ".bin"
        memory_file_name = "memory_" + str(time) + ".bin"
        dump(register_file_name, register_list)
        dump(memory_file_name, memory_list)
    code = code_list[pc][:32]  #code_list中每个元素的长是33，多了一个换行符，要去掉
    op_code = code[:6]
    bin_rs = code[6:11]
    rs = to_unsign_int(bin_rs)
    bin_rt = code[11:16]
    rt = to_unsign_int(bin_rt)
    bin_rd = code[16:21]
    rd = to_unsign_int(bin_rd)
    bin_sa = code[21:26]
    sa = to_unsign_int(bin_sa)
    function_code = code[26:]
    bin_immediate = code[16:]
    unsign_immediate = to_unsign_int(bin_immediate) #无符号
    sign_immediate = to_sign_int(bin_immediate)  #有符号
    bin_label = code[6:]
    if op_code == "000000":  #R
        if function_code_dict[function_code] == "add":   
            add(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "addu":   
            addu(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "and":   
            and_mips(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "div":   
            div(rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "divu":   
            divu(rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "jalr":   
            pc = jalr(rd, rs, pc)
            pc += 1
        elif function_code_dict[function_code] == "jr":   
            pc = jr(rs)
        elif function_code_dict[function_code] == "mfhi":   
            mfhi(rd)
            pc += 1
        elif function_code_dict[function_code] == "mflo":   
            mflo(rd)
            pc += 1
        elif function_code_dict[function_code] == "mthi":   
            mthi(rs)
            pc += 1
        elif function_code_dict[function_code] == "mtlo":   
            mtlo(rs)
            pc += 1
        elif function_code_dict[function_code] == "mult":   
            mult(rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "multu":   
            multu(rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "nor":   
            nor(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "or":   
            or_mips(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "sll":   
            sll(rd, rt, sa)
            pc += 1
        elif function_code_dict[function_code] == "sll":   
            sll(rd, rt, sa)
            pc += 1
        elif function_code_dict[function_code] == "sllv":   
            sllv(rd, rt, rs)
            pc += 1
        elif function_code_dict[function_code] == "slt":   
            slt(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "sltu":   
            sltu(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "sra":   
            sra(rd, rt, sa)
            pc += 1
        elif function_code_dict[function_code] == "srav":   
            srav(rd, rt, rs)
            pc += 1
        elif function_code_dict[function_code] == "srl":   
            srl(rd, rt, sa)
            pc += 1
        elif function_code_dict[function_code] == "srlv":   
            srlv(rd, rt, rs)
            pc += 1
        elif function_code_dict[function_code] == "sub":   
            sub(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "subu":   
            subu(rd, rs, rt)
            pc += 1
        elif function_code_dict[function_code] == "syscall":   
            program_break, exit_flag = syscall(time, exit_flag, program_break)
            pc += 1
        elif function_code_dict[function_code] == "xor":   
            xor(rd, rs, rt)
            pc += 1
    elif op_code_dict[op_code] == "addi":
        addi(rt, rs, sign_immediate)
        pc += 1
    elif op_code_dict[op_code] == "addiu":
        addiu(rt, rs, unsign_immediate)
        pc += 1
    elif op_code_dict[op_code] == "andi":
        andi(rt, rs, sign_immediate)
        pc += 1
    elif op_code_dict[op_code] == "beq":
        pc = beq(rs, rt, sign_immediate, pc)
    elif op_code_dict[op_code] == "bgez":
        pc = bgez(rs, sign_immediate, pc)
    elif op_code_dict[op_code] == "bgtz":
        pc = bgtz(rs, sign_immediate, pc)
    elif op_code_dict[op_code] == "blez":
        pc = blez(rs, sign_immediate, pc)
    elif op_code_dict[op_code] == "bltz":
        pc = bltz(rs, sign_immediate, pc)
    elif op_code_dict[op_code] == "bne":
        pc = bne(rs, rt, sign_immediate, pc)
    elif op_code_dict[op_code] == "lb":
        lb(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "lbu":
        lbu(rt, unsign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "lh":
        lh(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "lhu":
        lhu(rt, unsign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "lui":
        lui(rt, bin_immediate)
        pc += 1
    elif op_code_dict[op_code] == "lw":
        lw(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "ori":
        ori(rt, rs, unsign_immediate)
        pc += 1
    elif op_code_dict[op_code] == "sb":
        sb(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "slti":
        slti(rt, rs, sign_immediate)
        pc += 1
    elif op_code_dict[op_code] == "sltiu":
        sltiu(rt, rs, unsign_immediate)   
        pc += 1
    elif op_code_dict[op_code] == "sh":
        sh(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "sw":
        sw(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "xori":
        xori(rt, rs, unsign_immediate)
        pc += 1
    elif op_code_dict[op_code] == "lwl":
        lwl(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "lwr":
        lwr(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "swl":
        swl(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "swr":
        swr(rt, sign_immediate, rs)
        pc += 1
    elif op_code_dict[op_code] == "j":
        pc = j(bin_label, pc)
    elif op_code_dict[op_code] == "jal":
        pc = jal(bin_label, pc)

    register_list[32] = int("400000",16) + pc * 4
    
    time += 1

    print(time, " ", register_list)

# dump_memory("test.bin")


in_file.close()
out_file.close()


    
    
        
