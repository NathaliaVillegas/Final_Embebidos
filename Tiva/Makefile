#******************************************************************************
#
# Makefile - Rules for building the Tiva example.
#
# Defines the part type that this project uses.
#
PART=TM4C1294NCPDT

#
# The base directory for TivaWare.
#
ROOT=/home/nath/Documentos/SDKs/Tiva/TivaWare

#
# Include the common make definitions.
#
include ${ROOT}/makedefs

#
# Where to find header files that do not live in the source directory.
#
IPATH=/home/nath/Documentos/SDKs/Tiva/TivaWare

#
# The default rule, which causes the Tiva example to be built.
#
all: ${COMPILER}
all: ${COMPILER}/Tiva.axf

#
# The rule to clean out all the build products.
#
clean:
	@rm -rf ${COMPILER} ${wildcard *~}

#
# The rule to create the target directory.
#
${COMPILER}:
	@mkdir -p ${COMPILER}

#
# Rules for building the Tiva example.
#
${COMPILER}/Tiva.axf: ${COMPILER}/Tiva.o
${COMPILER}/Tiva.axf: ${COMPILER}/startup_${COMPILER}.o
${COMPILER}/Tiva.axf: ${ROOT}/driverlib/${COMPILER}/libdriver.a
${COMPILER}/Tiva.axf: Tiva.ld
SCATTERgcc_Tiva=Tiva.ld
ENTRY_Tiva=ResetISR
CFLAGSgcc=-DTARGET_IS_TM4C129_RA1

#
# Include the automatically generated dependency files.
#
ifneq (${MAKECMDGOALS},clean)
-include ${wildcard ${COMPILER}/*.d} __dummy__
endif
