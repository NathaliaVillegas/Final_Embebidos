#include <stdint.h>
#include <stdbool.h>

#include "inc/hw_memmap.h"
#include "inc/hw_ints.h"

#include "driverlib/sysctl.h"
#include "driverlib/gpio.h"
#include "driverlib/uart.h"
#include "driverlib/pin_map.h"
#include "driverlib/interrupt.h"

//====================================================
// VARIABLES GLOBALES 
//====================================================

volatile uint32_t total = 0;
volatile uint32_t respondidas = 0;
volatile uint32_t aciertos = 0;
volatile bool evento_r = false;
volatile bool evento_w = false;
volatile bool juego_activo = false;

char buffer[20];
uint8_t idx = 0;

//====================================================
// INTERRUPCIÓN UART3
//====================================================

void UART3IntHandler(void)
{
    uint32_t status = UARTIntStatus(UART3_BASE, true);
    UARTIntClear(UART3_BASE, status);

    while(UARTCharsAvail(UART3_BASE)){
        char c = UARTCharGetNonBlocking(UART3_BASE);
        
        if(c == '\n' || c == '\r'){
            buffer[idx] = '\0';
            idx = 0;
            
            if(buffer[0] == 'S'){
                uint32_t valor_temporal = 0;
                uint8_t i = 1;
                while(buffer[i] >= '0' && buffer[i] <= '9'){
                    valor_temporal = (valor_temporal * 10) + (buffer[i] - '0');
                    i++;
                }
                
                total = valor_temporal;
                aciertos = 0;
                respondidas = 0;
                juego_activo = true;
            }

            for(int i = 0; i < 20; i++){
                buffer[i] = '0';
            }
        }
        else{
            if(idx < sizeof(buffer)-1)
                buffer[idx++] = c;

            if(c == 'r') {
                idx = 0;
                if (juego_activo) {
                    evento_r = true;
                }
            }
            if(c == 'w') {
                idx = 0;
                if (juego_activo) {
                    evento_w = true;
                }
            }
        }
    }
}

//====================================================
// DELAY
//====================================================

void Delay_ms(uint32_t ms){
    SysCtlDelay((120000000 / 3000) * ms);
}

//====================================================
// LEDS INTERNOS PN0-PN3
//====================================================

void MostrarBinario(uint32_t numero){
    GPIOPinWrite(GPIO_PORTN_BASE, 0x0F, numero);
}

//====================================================
// CORRECTO
//====================================================

void EventoCorrecto(void){
    aciertos++;
    respondidas++;

    MostrarBinario(aciertos);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x01);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x02);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x04);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x07);
    Delay_ms(300);

    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x00);
}

//====================================================
// INCORRECTO
//====================================================

void EventoIncorrecto(void){
    respondidas++;

    GPIOPinWrite(GPIO_PORTM_BASE, 0x03, 0x03);
    Delay_ms(1000);
    GPIOPinWrite(GPIO_PORTM_BASE, 0x03, 0x00);
}

//====================================================
// CONFIG
//====================================================

void ConfigurarHardware(void)
{
    IntMasterDisable();

    //====================
    // PUERTO N
    //====================
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPION);
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPION));

    GPIOPinTypeGPIOOutput(GPIO_PORTN_BASE, 0x0F);
    GPIOPinWrite(GPIO_PORTN_BASE, 0x0F, 0x00);

    //====================
    // PUERTO K
    //====================
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOK);
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOK));

    GPIOPinTypeGPIOOutput(GPIO_PORTK_BASE,  0x07);
    GPIOPinWrite(GPIO_PORTK_BASE, 0x07, 0x00);

    //====================
    // PUERTO M
    //====================
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOM);
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOM));

    GPIOPinTypeGPIOOutput(GPIO_PORTM_BASE, 0x03);
    GPIOPinWrite(GPIO_PORTM_BASE, 0x03, 0x00);

    //====================
    // UART3 Config
    //====================
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART3);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOA);
    
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_UART3));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOA));

    GPIOPinConfigure(GPIO_PA4_U3RX);
    GPIOPinConfigure(GPIO_PA5_U3TX);
    GPIOPinTypeUART(GPIO_PORTA_BASE, 0x30);
    
    UARTConfigSetExpClk(UART3_BASE, 120000000, 9600, (UART_CONFIG_WLEN_8 | UART_CONFIG_STOP_ONE | UART_CONFIG_PAR_NONE));

    // Limpieza y activación de interrupciones para la UART3
    UARTIntClear(UART3_BASE, UART_INT_RX | UART_INT_RT);
    UARTIntEnable(UART3_BASE, UART_INT_RX | UART_INT_RT);
    IntEnable(INT_UART3);
}

//====================================================
// MAIN
//====================================================

int main(void)
{
    SysCtlClockFreqSet((SYSCTL_XTAL_25MHZ | SYSCTL_OSC_MAIN | SYSCTL_USE_PLL | SYSCTL_CFG_VCO_240), 120000000);

    ConfigurarHardware();
    IntMasterEnable();
    MostrarBinario(0);

    while(1){
        if(juego_activo){
            if(evento_r){
                evento_r = false;
                EventoCorrecto();
            }
            else if(evento_w){
                evento_w = false;
                EventoIncorrecto();
            }
        }

        if(juego_activo && respondidas >= total)
        {
            juego_activo = false;

            if((aciertos * 100) >= (total * 60)){
                MostrarBinario(0x0F);
            }
            else{
                MostrarBinario(0x00);
            }
        }
        Delay_ms(20);
    }
}