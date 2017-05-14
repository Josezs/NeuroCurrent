/*****************HJ-2WD慧净2驱WIFI智能小车例程*****************
*  平台：HJ-2WD/HJ-E/HL-1智能小车 + Keil U4 + STC89C52
*  名称：
*  公司：
*  淘宝：
*  网站：
*  编写：
*  日期：
*  交流:
*  晶振:11.0592MHZ
*  说明：
******************************************************************/
/*////////////////接线图//////////////////////////////////////////

MLA-----------------P1.0			L---left 左
MLB-----------------P1.1
MRA-----------------P1.2			R---right  右
MRB-----------------P1.3
////////////////////////////////////////////////////////////////*/
/*  Commandset
All commands are preceeded by string "Hello+"
One character command is next to the preceeding without space
There may be parameters 	depending on the commands
Commands:
'a': left mortor forward, parameter is time in milisecond
'b': Left mortor backward, parameter is time in milisecond
'c': Right mortor forward, same parameter
'd': Right mortor backward, same parameter
'r': Rotate left or right, when parameter>0 turn left, otherwise tern right

'h': Beeper, same parameter
*/

#include <stdio.h>
#include<AT89x51.H>
#define uchar unsigned char
#define uint unsigned int
#define FALSE 0
#define TRUE 1
#define LED_ZERO 0xC0
#define LED_ONE 0xF9
#define LED_TWO 0xA4
#define LED_THREE 0xB0
#define LED_FOUR 0x99
#define LED_FIVE 0x92
#define LED_SIX 0x82
#define LED_SEVEN 0xf8
#define LED_EIGHT 0x80
#define LED_NINE 0x90
#define LED_A 0x88
#define LED_B 0x83
#define LED_C 0xc6
#define LED_D 0xa1
#define LED_E 0x86
#define LED_F 0x8e
#define LED_POINT 0x7f

sbit BEEP=P2^6;
sbit LED0=P2^0;
sbit LED1=P2^1;

sbit Light1=P3^4;
sbit Light2=P3^5;
sbit Light3=P3^6;
sbit Light4=P3^7;

sbit M1A=P1^0;
sbit M1B=P1^1;
sbit M2A=P1^2;
sbit M2B=P1^3;
sbit M1E=P1^4;
sbit M2E=P1^5;

sbit SW1=P2^4;
sbit SW2=P2^5;
sbit SW3=P2^6;
sbit SW4=P2^7;

#define BUF_SIZE 20
#define BUF_END  0
uchar send_buff[BUF_SIZE];
uint buf_send_ptr;
uint buf_fill_ptr;
uchar sending;

#define RCV_BUF_SIZE 40
uchar rcv_buf[RCV_BUF_SIZE];
uint rcv_cnt, read_cnt; 

#define CMD_BUF_SIZE 20
uint cmd_cnt;
uchar cmd_buf[CMD_BUF_SIZE];

#define DELAY_Q_SIZE 5
struct  delay_q_str{
uchar counting_flag;
uchar over_flow;
uint count;
void (*action)();
} delay_q[DELAY_Q_SIZE];
uint counter;
uchar timer_over_flow;


void rcv_buf_init()
{
	rcv_cnt=0;
	read_cnt=RCV_BUF_SIZE-1;
	cmd_cnt = 0;
}

int read_cmd()
{
	uint cnt;

	while (TRUE) {
		cnt = read_cnt + 1;
		if (cnt == RCV_BUF_SIZE)
			cnt = 0;
		if (cnt != rcv_cnt) {
			cmd_buf[cmd_cnt] = rcv_buf[cnt];
			read_cnt = cnt;
		} else
			return FALSE;
		if ((cmd_buf[cmd_cnt] == '\r') || (cmd_buf[cmd_cnt] == '\n'))
		{
			if (cmd_cnt>0)
			{
				cmd_buf[cmd_cnt]=0;
				cmd_cnt=0;
				return TRUE;
			}
		} else {
			cmd_cnt++;
			if (cmd_cnt==CMD_BUF_SIZE-1)
			{
				//cmd_buf[cmd_cnt]=0;
				cmd_cnt=0;
				//return TRUE;
			}
		}
	} 
}

void delay_q_init()
{
	int i;

	for(i=0;i<DELAY_Q_SIZE;i++)
	{
		delay_q[i].counting_flag=FALSE;
		delay_q[i].over_flow=FALSE;
		delay_q[i].count=0;
		delay_q[i].action=0;
	}
	counter=0;
	timer_over_flow = FALSE;
}

int set_delay(int delay_num, uint delay, void (*action)())
{
	uint count;

	if (delay_num>=DELAY_Q_SIZE)
		return FALSE;
	if (delay_q[delay_num].counting_flag != FALSE)
		return  FALSE; 
	count = counter+delay;
	if (count<delay)
		delay_q[delay_num].over_flow = TRUE;
	else
		delay_q[delay_num].over_flow = FALSE;
 	delay_q[delay_num].count = count;
	delay_q[delay_num].action = action;
	delay_q[delay_num].counting_flag = TRUE;
	return TRUE	;
}

void proc_time_out()
{
	int i;

	if (timer_over_flow == TRUE){
		for (i=0;i<DELAY_Q_SIZE;i++)
		{
			if ((delay_q[i].counting_flag) && 
			    (delay_q[i].over_flow == FALSE))
			{
					(*delay_q[i].action)();
					delay_q[i].counting_flag = FALSE;
			}
			delay_q[i].over_flow = FALSE;
		}
		timer_over_flow = FALSE;
	}
	for (i=0;i<DELAY_Q_SIZE;i++)
	{
		if (delay_q[i].counting_flag) {
			if (counter>=delay_q[i].count) {
				(*delay_q[i].action)();
				delay_q[i].counting_flag = FALSE;
			}
		}
	} 
}


void send_buf_init()
{
	int i;
	buf_send_ptr = 0;
	buf_fill_ptr = 0;
	sending = FALSE;
	for (i=0;i<BUF_SIZE;i++)
		send_buff[i] = BUF_END;
}

void send_str(uchar str[])
{	int i;
	i = 0;
	while (str[i]  != BUF_END) {
		if (send_buff[buf_fill_ptr] != BUF_END) 
			break;
		send_buff[buf_fill_ptr] = str[i];
		i++;
		buf_fill_ptr++;
		if (buf_fill_ptr>=BUF_SIZE)
			buf_fill_ptr = 0;
	}
	if (FALSE == sending) {
		SBUF=send_buff[buf_send_ptr];
		sending = TRUE;
		send_buff[buf_send_ptr] = BUF_END;
		buf_send_ptr++;
		if (buf_send_ptr>=BUF_SIZE)
			buf_send_ptr = 0;
	}
}

uchar bin2hex4(uchar ch)
{
	int  temp;
	temp = ch & 0x0f;
	if (temp < 10)
		return temp+'0';
	temp = temp - 10;
	return temp+'A';
}

void send_hex(uchar ch)
{
	uchar buf[10];
	
	buf[0] = bin2hex4(ch>>4);
	buf[1] = bin2hex4(ch);
	buf[2] = 10;
	buf[3] = 13;
	buf[4] = BUF_END;
	send_str(buf); 
}

void Com_Init()
{
   	//IE	= 0x00;			//停止所有中断
	TMOD= 0x22;			//设置定时器0、1为方式2（8位自动重装）
	SCON= 0x50;			//设置串口控制寄存器，串口方式1,10位uart，波特率可调；允许接收
	TH1	= TL1 = 0xfd;	//为定时器1赋初值，晶振为11.0592MHz时波特率为9600bps
	IE	= 0x92;			//开定时器0中断，串口中断，外中断0和总中断
	//EA,_ _ ES,ET1,EX1,ET0,EX0
	TR1	= 1;	
}

void Time0_Init()	 //定时器初始化
{
	//T0在Com_Init()中初始化为模式2
	TH0=TL0=(256-(200*11.0592/12));	//计时200us，时钟11.0592MHz, 12周期记一次
	TR0=1;   
}

void left_mot_fwd()
{
	M1A=1;
	M1B=0;
	M1E=1;
}
void left_mot_stop()
{
	M1A=0;
	M1B=0;
	M1E=0;
}

void left_mot_bkwd()
{
	M1A=0;
	M1B=1;
	M1E=1;
}

void right_mot_fwd()
{
	M2A=1;
	M2B=0;
	M2E=1;
}

void right_mot_stop()
{
	M2A=0;
	M2B=0;
	M2E=0;
}

void right_mot_bkwd()
{
	M2A=0;
	M2B=1;
	M2E=1;
}

void right_fwd_left_bk()
{
	right_mot_fwd();
	left_mot_bkwd();
}

void left_fwd_right_bk()
{
	left_mot_fwd();
	right_mot_bkwd();
}

void both_mot_stop()
{
	left_mot_stop();
	right_mot_stop();
}

void set_beep()
{
	BEEP=0;
}

void clear_beep()
{
	BEEP=1;
}

void main()
{
	int delay,addr;

	delay_q_init();
	send_buf_init();
	rcv_buf_init();

	P0=0xff;   //ef
	P1=0x00;   //00
	P2=0xff;   //ff
	P3=0xff;   //ff
	Time0_Init();
	Com_Init();
	 
	LED0=0;
	while(1)
	{
		if (!SW1) {
			BEEP = 0;
			set_delay(4,200,&clear_beep);
			P0=LED_A;
		}
		if (!SW2) {
			BEEP=0;
			set_delay(4,400,&clear_beep);
			P0='\n';
		}
		if (!SW4) {
			BEEP = 1;
			P0=LED_C;
			set_delay(4,1600,&clear_beep);
		}
		proc_time_out();
		if (read_cmd() == TRUE)
		{
			send_str(cmd_buf);
			send_str("\r\n");
			//send_hex(read_cnt);
			//send_hex(rcv_cnt);
			send_hex(cmd_buf[0]);
			if (( 'H' == cmd_buf[0]) &&
				('e' == cmd_buf[1]) &&
				('l' == cmd_buf[2]) &&
				('l' == cmd_buf[3]) &&
				('o' == cmd_buf[4]) &&
				('+' == cmd_buf[5] ))
			{
				switch  (cmd_buf[6])   {
				case 'a':{
					sscanf(cmd_buf+7,"%d",&delay);
					P0= (delay&0x0ff);
					left_mot_fwd();
					set_delay(0,delay+1, &left_mot_stop);
					break;}
				case 'b':{
					sscanf(cmd_buf+7,"%d",&delay);
					P0=delay&0x0ff;
					left_mot_bkwd();
					set_delay(0,delay+1, &left_mot_stop);
					break;}
				case 'c':{
					sscanf(cmd_buf+7,"%d",&delay);
					P0=delay&0x0ff;
					right_mot_fwd();
					set_delay(1,delay+1, &right_mot_stop);
					break;}
				case 'd':{
					sscanf(cmd_buf+7,"%d",&delay);
					P0=LED_D;
					right_mot_bkwd();
					set_delay(1,delay+1, &right_mot_stop);
					break;}
				case 'r':{
					sscanf(cmd_buf+7,"%d",&delay);
					if (delay>0)
						right_fwd_left_bk();
					else {
						delay = -delay;
						left_fwd_right_bk();
					}
					set_delay(2,delay+1,&both_mot_stop);
					break;}
				case 'h':{
					sscanf(cmd_buf+7,"%d",&delay);
					set_beep();
					P0=delay&0x0ff;
					set_delay(4,delay+1,&clear_beep);
					break;}
				default:{
					P0=LED_D;
					//set_beep();
					BEEP=0;
					set_delay(4,1000,&clear_beep);
					break;}
				}
			} else {
				P0=LED_F;
				//set_beep();
				//set_delay(4,100,&clear_beep);
			}
		}
	}	
}

void Time0_Int() interrupt 1
{
	counter++;
	if (0 == counter)
		timer_over_flow = TRUE;
}


void ser() interrupt 4
{
	uchar command=0;
	
	ES=0;	  //关闭串口c中断

// 	P0=LED_A;
	if (TI) {
		TI = 0;
		if (send_buff[buf_send_ptr] != BUF_END){
			SBUF=send_buff[buf_send_ptr];
			sending = TRUE;
			send_buff[buf_send_ptr] = BUF_END;
			buf_send_ptr++;
			if (buf_send_ptr>=BUF_SIZE)
				buf_send_ptr = 0;
		}
		else
			sending = FALSE;
	}	  
	if(RI) {
		RI=0;	          //清除口接收标志位
		command=SBUF;	  //读取字符	
		switch(command)	 	{
		case 'h':{					  
			  BEEP=0;
			  break;
		    }							
		case 'i':{					  
			  BEEP=1;
			  break;
		    }
		case 's':{
			send_str(cmd_buf);
			send_str("\r\n");
			break;
			}							
   		default:
            {
			BEEP=1;
			break;
			}
		}
		if (rcv_cnt != read_cnt) {
			rcv_buf[rcv_cnt]=command;
			rcv_cnt++;
			if (rcv_cnt==RCV_BUF_SIZE)
				rcv_cnt=0;
		}
		//P0=command;
    }
	ES=1;	//允许串口中断				
}
	  
