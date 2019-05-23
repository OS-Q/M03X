import xml.etree.ElementTree as ET
import os

binariesText = "\n\
PREFIX = arm-none-eabi-\n\
# The gcc compiler bin path can be either defined in make command via GCC_PATH variable (> make GCC_PATH=xxx)\n\
# either it can be added to the PATH environment variable.\n\
ifdef GCC_PATH\n\
CC = $(GCC_PATH)/$(PREFIX)gcc-\
AS = $(GCC_PATH)/$(PREFIX)gcc -x assembler-with-cpp\n\
CP = $(GCC_PATH)/$(PREFIX)objcopy\n\
SZ = $(GCC_PATH)/$(PREFIX)size\n\
else\n\
CC = $(PREFIX)gcc\n\
AS = $(PREFIX)gcc -x assembler-with-cpp\n\
CP = $(PREFIX)objcopy\n\
SZ = $(PREFIX)size\n\
endif\n\
HEX = $(CP) -O ihex\n\
BIN = $(CP) -O binary -S"

buildText = "\n\
# list of objects\n\
OBJECTS = $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))\n\
vpath %.c $(sort $(dir $(C_SOURCES)))\n\
# list of ASM program objects\n\
OBJECTS += $(addprefix $(BUILD_DIR)/,$(notdir $(ASM_SOURCES:.s=.o)))\n\
vpath %.s $(sort $(dir $(ASM_SOURCES)))\n\n\
$(BUILD_DIR)/%.o: %.c Makefile | $(BUILD_DIR)\n\
	$(CC) -c $(CFLAGS) -Wa,-a,-ad,-alms=$(BUILD_DIR)/$(notdir $(<:.c=.lst)) $< -o $@\n\n\
$(BUILD_DIR)/%.o: %.s Makefile | $(BUILD_DIR)\n\
	$(AS) -c $(CFLAGS) $< -o $@\n\n\
$(BUILD_DIR)/$(TARGET).elf: $(OBJECTS) Makefile\n\
	$(CC) $(OBJECTS) $(LDFLAGS) -o $@\n\
	$(SZ) $@\n\n\
$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf | $(BUILD_DIR)\n\
	$(HEX) $< $@\n\n\
$(BUILD_DIR)/%.bin: $(BUILD_DIR)/%.elf | $(BUILD_DIR)\n\
	$(BIN) $< $@\n\n\
$(BUILD_DIR):\n\
	mkdir $@\n"

def makeComment(name):
	return 40*"#"+"\n# "+name+"\n"+40*"#"

def getFromProj(projFile):
	includes = {
		'TARGET':'',
		'CPU' : '-mcpu=',
		'C_INCLUDES':'',
		'C_DEFS':'',
	}

	tree = ET.parse(projFile)
	root = tree.getroot()
	files = set()
	extensions = set()
	for element in tree.iter(tag='FilePath'):
		if element.text:
			files.add(element.text.replace('\\', '/'))
			extensions.add(os.path.splitext(element.text.replace('\\', '/'))[1])
	for element in tree.iter(tag='OutputName'):
		if element.text:
			includes['TARGET'] = element.text
	for element in tree.iter(tag='AdsCpuType'):
		if element.text:
			includes['CPU'] += element.text.lower()


	# INCLUDES
	directory = []
	for element in tree.iter(tag='IncludePath'):
		if element.text:
			directory += element.text.replace('\\', '/').split(';')
	inc = set(directory)
	inc = sorted(inc)
	for element in inc:
		includes['C_INCLUDES'] += ' \\ \n-I' + element

	# DEFINES
	directory = []
	for element in tree.iter(tag='Define'):
		if element.text:
			directory += element.text.split(',')
	inc = set(directory)
	inc = sorted(inc)
	for element in inc:
		includes['C_DEFS'] += ' \\ \n-D' + element

	return includes

def getFromOpt(optFile):
	sources = {
			'C_SOURCES':'',
			'ASM_SOURCES':'',
	}
	tree = ET.parse(optFile)
	root = tree.getroot()
	files = set()
	extensions = set()
	for element in tree.iter(tag='PathWithFileName'):
		if element.text:
			files.add(element.text.replace('\\', '/'))
			extensions.add(os.path.splitext(element.text.replace('\\', '/'))[1])

	files = sorted(files)
	extensions=sorted(extensions)
	for i in extensions:
		#print (i + " Files: -----------------------------")
		for element in files:
			if(os.path.splitext(element)[1] == i): #Si la extensión coincide
				if  (i==".c"):
					sources['C_SOURCES'] += ' \\'+'\n' + element
				elif(i==".s"):
					sources['ASM_SOURCES'] += ' \\'+'\n' + element

	return sources

listing = {
		'TARGET':'',
		'DEBUG':'1',
		'OPT':'-Og',
		'BUILD_DIR':'build',
		'C_SOURCES':'',
		'ASM_SOURCES':'',
		'binaries':'',
		'CPU':'',
		'FPU':'-mfpu=fpv5-sp-d16',
		'FLOAT-ABI':'-mfloat-abi=hard',
		'MCU':'$(CPU) -mthumb $(FPU) $(FLOAT-ABI)',
		'AS_DEFS':'',
		'C_DEFS':'',
		'AS_INCLUDES':'',
		'C_INCLUDES':'',
		'ASFLAGS':'$(MCU) $(AS_DEFS) $(AS_INCLUDES) $(OPT) -Wall '+
				'-fdata-sections -ffunction-sections',
		'CFLAGS':'$(MCU) $(C_DEFS) $(C_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections\n\n'+
				'ifeq ($(DEBUG), 1)\n'+
				'CFLAGS += -g -gdwarf-2\n'+
				'endif\n\n'+
				'# Generate dependency information\n'+
				'CFLAGS += -MMD -MP -MF\"$(@:%.o=%.d)\"',
		'LDSCRIPT':'STM32F746NGHx_FLASH.ld',
		'LIBS':'-lc -lm -lnosys',
		'LIBDIR':'',
		'LDFLAGS':'$(MCU) -specs=nano.specs -T$(LDSCRIPT) $(LIBDIR) $(LIBS)'+
				'-Wl,-Map=$(BUILD_DIR)/$(TARGET).map,--cref -Wl,--gc-sections'


}

listing.update(getFromProj('Project.uvprojx'))
listing.update(getFromOpt('Project.uvoptx'))
#print(listing['C_SOURCES'])

todoList = {
		'target':['TARGET'],
		'building variables':['DEBUG','OPT'],
		'paths':['BUILD_DIR'],
		'source':['C_SOURCES','ASM_SOURCES'],
		'binaries':[binariesText],
		'CFLAGS':['CPU','FPU','FLOAT-ABI','MCU','AS_DEFS',
				'C_DEFS','AS_INCLUDES','C_INCLUDES','ASFLAGS','CFLAGS'],
		'LDFLAGS':['LDSCRIPT','LIBS','LIBDIR','LDFLAGS',
				"all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin"],
		'build the application':[buildText],
		'clean up':['clean:\n\t-rm -fR $(BUILD_DIR)'],
		'Flash it!':['flash: $(BUILD_DIR)/$(TARGET).bin\n'+
				'\tst-flash write $(BUILD_DIR)/$(TARGET).bin 0x8000000'],
		'dependencies':['-include $(wildcard $(BUILD_DIR)/*.d)'],
}

def main():
	for key,val in todoList.items():
		print()
		print(makeComment(key))
		for i in val:
			if(i in listing):
				print(i + " = " + str(listing[i]) + "\n")
			else:
				print(i)


if __name__== "__main__":
  main()
