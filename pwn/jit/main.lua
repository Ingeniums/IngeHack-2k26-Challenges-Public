local ffi = require("ffi")

function addr(val)
    local VIEW = ffi.cast("uint64_t*", val)
    return VIEW
end

function split_space(str) 
    local result = {}
    for value in str:gmatch("%S+") do
        table.insert(result, value)
    end
    return result
end

function is_number(val)
    return tonumber(val) ~= nil
end

function print_menu()
    print("=== Stacking Machine ===")
    print("push val")
    print("pop")
    print("set idx val")
    print("get idx")
    io.write(">> ")
    io.flush()
end


local ARRAY = ffi.new("uint64_t[10]")
local STACK_STATE = ffi.new("uint64_t[2]")
local STACK = ffi.new("uint64_t[20]")
ARRAY_SIZE = 0x10
STACK_STATE[1] = 0
STACK_STATE[2] = 20




addr(ARRAY)

while true do
    print_menu()
    input = io.read()
    cmd = split_space(input)[1]

    if cmd == "push" then
        val = split_space(input)[2]
        if val == nil then
            print("at least send smth")
            os.exit()
        end

        if not is_number(val) then
            print("never heard of this")
            os.exit()
        end

        if STACK_STATE[1] > STACK_STATE[2] then
            print("smth is off, maybe a pwner is here")
            os.exit()
        end 

        if STACK_STATE[1] == STACK_STATE[2] then
            print("too much")
            goto continue
        end 


        val = tonumber(val)
        STACK_STATE[1] = STACK_STATE[1] + 1
        STACK[STACK_STATE[1]] = val

    elseif cmd == "pop" then 
        if STACK_STATE[1] == 0 then
            print("too little")
            goto continue
        end 

        val = STACK[STACK_STATE[1]]
        STACK_STATE[1] = STACK_STATE[1] - 1
        print(val)


    elseif cmd == "set" then
        idx = split_space(input)[2]
        if idx == nil then
            print("mmm")
            os.exit()
        end 
        
        if not is_number(idx) then
            print("never heard of this")
            os.exit()
        end
        idx = tonumber(idx)



        val = split_space(input)[3]
        if val == nil then
            print("so nil?")
            os.exit()
        end 

        if not is_number(val) then
            print("never heard of this")
            os.exit()
        end
        val = tonumber(val)


        if idx < 0 or idx > ARRAY_SIZE then
            print("out of range")
            goto continue
        end



        ARRAY[idx] = val
    elseif cmd == "get" then
        idx = split_space(input)[2]
        if idx == nil then
            print("mmm")
            goto continue
        end 
        if not is_number(idx) then
            print("never heard of this")
            os.exit()
        end

        idx = tonumber(idx)
        
        if idx < 0 or idx > ARRAY_SIZE then
            print("out of range")
            goto continue
        end



        val = ARRAY[idx]
        print(val)
    else
        print("what?")
        goto exit
    end


    ::continue::
end


::exit::

print(":P")
