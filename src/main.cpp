#include <Arduino.h>

// adcdma
//  analog A0
//   could use DAC to provide input voltage   A0
//   http://www.atmel.com/Images/Atmel-42258-ASF-Manual-SAM-D21_AP-Note_AT07627.pdf pg 73
#define ADCPIN A0
#define HWORDS 1
#define EXT0_PORT PORTA
#define EXT0_PIN_NUMBER A7
#define EXT0_PIN_MASK PORT_PA07
#define TEST_LED 13
#define DATA_LIMIT 2500
typedef enum
{
    NONE,
    GOT_G, // get data from memory and send across serial
    GOT_L, // capture limit, send this many data points per trigger
    GOT_R, // set receive status
    GOT_S, // serial write all data to counter out
    GOT_T, // trigger capture

} states;

states state = NONE;

int current_value = 0;
bool data_ready = 0;
long time_elapsed = 0;
long time_last = 0;
int delay_period = 1000;
uint16_t test_result = 0;

volatile int counter = 0;
volatile int write_counter = 0;
int transfer_done = false;

uint16_t data[DATA_LIMIT];
long time_us[DATA_LIMIT];
long acq_time[DATA_LIMIT];
int capture_limit = 100;
long trigger_time = 0;
int led_state = 0;

const int RESET_CNT_PIN = 9;
const int ADC_TRIG_PIN = 4;
const int LED_FEEDBACK = 7;
const int READY_BTN = 6;
uint16_t sample = 0;
bool measure_state = 0;

uint16_t adcbuf[HWORDS];

typedef struct
{
    uint16_t btctrl;
    uint16_t btcnt;
    uint32_t srcaddr;
    uint32_t dstaddr;
    uint32_t descaddr;
} dmacdescriptor;
volatile dmacdescriptor wrb[12] __attribute__((aligned(16)));
dmacdescriptor descriptor_section[12] __attribute__((aligned(16)));
dmacdescriptor descriptor __attribute__((aligned(16)));

static uint32_t chnl = 0; // DMA channel
volatile uint32_t dmadone;

void DMAC_Handler()
{
    // interrupts DMAC_CHINTENCLR_TERR DMAC_CHINTENCLR_TCMPL DMAC_CHINTENCLR_SUSP
    uint8_t active_channel;

    // disable irqs ?
    // __disable_irq();
    active_channel = DMAC->INTPEND.reg & DMAC_INTPEND_ID_Msk; // get channel number
    DMAC->CHID.reg = DMAC_CHID_ID(active_channel);
    dmadone = DMAC->CHINTFLAG.reg;
    DMAC->CHINTFLAG.reg = DMAC_CHINTENCLR_TCMPL; // clear
    DMAC->CHINTFLAG.reg = DMAC_CHINTENCLR_TERR;
    DMAC->CHINTFLAG.reg = DMAC_CHINTENCLR_SUSP;
    // __enable_irq();
}

void dma_init()
{
    // probably on by default
    PM->AHBMASK.reg |= PM_AHBMASK_DMAC;
    PM->APBBMASK.reg |= PM_APBBMASK_DMAC;
    DMAC->BASEADDR.reg = (uint32_t)descriptor_section;
    DMAC->WRBADDR.reg = (uint32_t)wrb;
    DMAC->CTRL.reg = DMAC_CTRL_DMAENABLE | DMAC_CTRL_LVLEN(0xf);

    // disable interrupt
    NVIC_DisableIRQ(DMAC_IRQn);

    // clear device specific interrupt from pending
    NVIC_ClearPendingIRQ(DMAC_IRQn);

    /// change its priority to the highest
    NVIC_SetPriority(DMAC_IRQn, 0);
    // reenable interrupt
    NVIC_EnableIRQ(DMAC_IRQn);
}

void adc_dma(void *rxdata, size_t hwords)
{
    uint32_t temp_CHCTRLB_reg;

    DMAC->CHID.reg = DMAC_CHID_ID(chnl);
    DMAC->CHCTRLA.reg &= ~DMAC_CHCTRLA_ENABLE;
    DMAC->CHCTRLA.reg = DMAC_CHCTRLA_SWRST;
    DMAC->SWTRIGCTRL.reg &= (uint32_t)(~(1 << chnl));
    temp_CHCTRLB_reg = DMAC_CHCTRLB_LVL(0) |
                       DMAC_CHCTRLB_TRIGSRC(ADC_DMAC_ID_RESRDY) | DMAC_CHCTRLB_TRIGACT_BEAT;
    DMAC->CHCTRLB.reg = temp_CHCTRLB_reg;
    DMAC->CHINTENSET.reg = DMAC_CHINTENSET_MASK; // enable all 3 interrupts
    dmadone = 0;
    descriptor.descaddr = 0;
    descriptor.srcaddr = (uint32_t)&ADC->RESULT.reg;
    descriptor.btcnt = hwords;
    descriptor.dstaddr = (uint32_t)rxdata + hwords * 2; // end address
    descriptor.btctrl = DMAC_BTCTRL_BEATSIZE_HWORD | DMAC_BTCTRL_DSTINC | DMAC_BTCTRL_VALID;
    memcpy(&descriptor_section[chnl], &descriptor, sizeof(dmacdescriptor));

    // start channel
    DMAC->CHID.reg = DMAC_CHID_ID(chnl);
    DMAC->CHCTRLA.reg |= DMAC_CHCTRLA_ENABLE;
}

static __inline__ void ADCsync() __attribute__((always_inline, unused));
static void ADCsync()
{
    while (ADC->STATUS.bit.SYNCBUSY == 1)
        ; // Just wait till the ADC is free
}

void adc_init()
{
    analogRead(ADCPIN);           // do some pin init  pinPeripheral()
    ADC->CTRLA.bit.ENABLE = 0x00; // Disable ADC
    ADCsync();
    // ADC->REFCTRL.bit.REFSEL = ADC_REFCTRL_REFSEL_INTVCC0_Val; //  2.2297 V Supply VDDANA
    // ADC->INPUTCTRL.bit.GAIN = ADC_INPUTCTRL_GAIN_1X_Val;      // Gain select as 1X
    ADC->INPUTCTRL.bit.GAIN = ADC_INPUTCTRL_GAIN_DIV2_Val; // default
    ADC->REFCTRL.bit.REFSEL = ADC_REFCTRL_REFSEL_INTVCC1_Val;
    ADCsync(); //  ref 31.6.16
    ADC->INPUTCTRL.bit.MUXPOS = g_APinDescription[ADCPIN].ulADCChannelNumber;
    ADCsync();
    ADC->AVGCTRL.reg = 0x00; // no averaging
    ADC->SAMPCTRL.reg = 0x00;
    ; // sample length in 1/2 CLK_ADC cycles
    ADCsync();
    ADC->CTRLB.reg = ADC_CTRLB_PRESCALER_DIV16 | ADC_CTRLB_FREERUN | ADC_CTRLB_RESSEL_12BIT;
    ADCsync();
    ADC->CTRLA.bit.ENABLE = 0x01;
    ADCsync();
}

void adc_trigger()
{
    if (measure_state == 1)
    {
        sample = 0;
        time_us[counter] = micros();
        adc_dma(adcbuf, HWORDS);
        while (!dmadone)
            ; // await DMA done isr
        if (HWORDS > 1)
        {
            for (int i = 0; i < HWORDS; i++)
            {
                sample += adcbuf[i];
            }
            data[counter] = (uint16_t)(sample / HWORDS);
        }
        else
        {
            data[counter] = adcbuf[0];
        }
        acq_time[counter] = micros();
        counter++;
    }
}

void extInt_init()
{
    attachInterrupt(EXT0_PIN_NUMBER, adc_trigger, RISING);
    NVIC_DisableIRQ(EIC_IRQn);
    NVIC_ClearPendingIRQ(EIC_IRQn);
    NVIC_SetPriority(EIC_IRQn, 5);
    NVIC_EnableIRQ(EIC_IRQn);
}

void testLED_init()
{
    // enable input, to support reading back values, with pullups disabled
    PORT->Group[PORTA].PINCFG[TEST_LED].reg = (uint8_t)(PORT_PINCFG_INEN);
    // Set pin to output mode
    PORT->Group[PORTA].DIRSET.reg = (1ul << TEST_LED);
}

void retrieve_state()
{
    Serial.print("counter: ");
    Serial.print(counter);
    Serial.print(", write_counter: ");
    Serial.println(write_counter);
}

void get_data(int num_data_points)
{
    // nothing
}

void toggle_capture()
{
    Serial.flush();
    counter = 0;
    write_counter = 0;
    measure_state = 1;
    transfer_done = 0;
}

void set_capture_limit(int current_value)
{
    capture_limit = current_value;
}

void handle_action()
{
    switch (state)
    {
    case GOT_G:
        get_data(current_value);
        break;
    case GOT_L:
        set_capture_limit(current_value);
        break;
    case GOT_R:
        retrieve_state();
        break;
    case GOT_S:
        break;
    case GOT_T:
        toggle_capture();
        break;
    default:
        break;
    } // end of switch

    // action has been handled, reset value and state for next command
    current_value = 0; // since we utilized the current_value above, now we reset it to zero for the next variable
    state = NONE;      // set the state to none, as we have used it
}

void process_inc_byte(const byte c)
{

    if (isdigit(c))
    {
        current_value *= 10;
        current_value += c - '0';
    } // end of digit
    else
    {
        // set the new state if we recognize
        switch (c)
        {
        case ';':
            handle_action();
            break;
        case 'g':
            state = GOT_G;
            break;
        case 'l':
            state = GOT_L;
            break;
        case 'r':
            state = GOT_R;
            break;
        case 's':
            state = GOT_S;
            break;
        case 't':
            state = GOT_T;
            break;
        default:
            state = NONE;
            break;
        } // end switch
    }     // end of not digit
}

void send_data_point(int wrt_cnt)
{
    if (wrt_cnt >= capture_limit)
    {
        Serial.println(";");
        transfer_done = 1;
    }
    else
    {
        Serial.print(wrt_cnt);
        Serial.print(",");
        Serial.print(time_us[wrt_cnt] - time_us[0]);
        Serial.print(",");
        Serial.print(acq_time[wrt_cnt] - time_us[wrt_cnt]);
        Serial.print(",");
        Serial.println(data[wrt_cnt]);
    }
}

void setup()
{
    Serial.begin(115200);
    testLED_init();
    adc_init();
    dma_init();
    extInt_init();
}

void loop()
{
    while (Serial.available())
    {
        process_inc_byte(Serial.read());
    }

    if (counter <= capture_limit)
    {
        digitalWrite(LED_BUILTIN, LOW);
        delay(100);
        digitalWrite(LED_BUILTIN, HIGH);
        delay(100);
    }

    if (counter >= capture_limit)
    {
        digitalWrite(LED_BUILTIN, LOW);
        while (write_counter <= capture_limit)
        {
            send_data_point(write_counter);
            write_counter++;
        }
        digitalWrite(LED_BUILTIN, HIGH);
    }

    // if (write_counter >= capture_limit)
    // {
    //     Serial.println("data_end;");
    // }
    // else
    // {
    //     Serial.print("wc_");
    //     Serial.print(write_counter);
    //     Serial.print("_c_");
    //     Serial.print(counter);
    // }

    // if ((measure_state == 1) && (write_counter == counter) && (counter >= capture_limit))
    // {
    //     Serial.println("data_end;");
    //     measure_state = 0;
    // }
}
